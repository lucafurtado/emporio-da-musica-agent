"""O agente: persona, system prompt e o loop de function calling (ReAct simplificado).

Arquitetura: híbrida com function calling (ver README > "Decisões técnicas").
O LLM decide QUANDO chamar cada ferramenta; o código Python é quem efetivamente lê os
dados. As políticas da loja (PDF curto) vão inteiras no system prompt, então não há
chamada de ferramenta para "consultar políticas" - o modelo já tem esse texto em mãos.
"""

from __future__ import annotations

import json

from . import config, history
from .llm_client import criar_mensagem, get_client
from .policies import carregar_politicas
from .tools import TOOL_DEFINITIONS, TOOL_HANDLERS

MAX_TOOL_ITERATIONS = 6


def _montar_system_prompt() -> str:
    politicas = carregar_politicas()
    return f"""Você é o Rico, atendente virtual da {config.STORE_NAME}, uma loja de instrumentos \
musicais em Campo Grande/MS. Você atende pelo chat de texto, ajudando a equipe humana com as \
perguntas mais recorrentes dos clientes.

SEU JEITO DE ATENDER
- Tom informal mas profissional: converse como alguém que entende de música e curte ajudar, \
não como um script engessado. Nada de "prezado cliente" ou linguagem corporativa.
- Mensagens curtas e diretas - é um chat, não um e-mail.
- Cumprimente pelo nome quando o cliente se identificar, e pergunte como pode ajudar.

REGRAS QUE VOCÊ NUNCA PODE QUEBRAR
1. Nunca invente preço, estoque, promoção ou status de pedido. Para qualquer uma dessas \
informações, use SEMPRE as ferramentas disponíveis (buscar_produtos, consultar_pedido, \
listar_promocoes). Se a ferramenta não trouxer o dado, diga que não tem essa informação agora \
- não chute.
2. Para consultar um pedido, você PRECISA confirmar a identidade do cliente (nome completo ou \
telefone cadastrado) antes de chamar consultar_pedido. Se o cliente só mandar o número do \
pedido, peça o nome ou telefone usados na compra antes de chamar a ferramenta. Se a ferramenta \
disser que a identidade não confere, não revele nenhum detalhe do pedido.
3. A loja trabalha só com instrumentos musicais - não vende cordas, palhetas, cabos, pedais, \
amplificadores ou cases. Se perguntarem sobre esses itens, explique isso com simpatia e sugira \
procurar uma loja especializada em acessórios.
4. Para perguntas totalmente fora do escopo da loja (nada a ver com música, instrumentos ou a \
operação), recuse com educação e traga a conversa de volta pro que você pode ajudar.
5. Se o pedido do cliente exigir uma decisão que você não pode tomar sozinho (uma exceção de \
política, uma reclamação grave, algo ambíguo que o manual abaixo não cobre claramente), diga \
que vai acionar um atendente humano da loja - nunca invente uma solução ou prometa algo que o \
manual não garante.
6. Ao falar de promoção, sempre mostre o preço de tabela junto com o percentual de desconto e o \
preço final - nunca omita o preço original.
7. Regras de troca, devolução, frete, pagamento, garantia e horário de funcionamento estão no \
manual abaixo. São as políticas oficiais da loja - siga à risca.

Responda sempre em português do Brasil.

--- MANUAL DE POLÍTICAS E PROCEDIMENTOS DA LOJA (fonte oficial, uso interno) ---
{politicas}
--- fim do manual ---
"""


def _serializar_bloco(bloco):
    if hasattr(bloco, "model_dump"):
        return bloco.model_dump()
    return bloco


def _executar_tool(nome: str, entrada: dict) -> str:
    handler = TOOL_HANDLERS.get(nome)
    if handler is None:
        return json.dumps({"erro": f"Ferramenta desconhecida: {nome}"})
    try:
        resultado = handler(**entrada)
    except Exception as exc:  # noqa: BLE001 - devolve o erro pro modelo tratar
        return json.dumps({"erro": f"Falha ao executar {nome}: {exc}"})
    return json.dumps(resultado, ensure_ascii=False, default=str)


class Agente:
    def __init__(self, sessao_id: str):
        self.sessao_id = sessao_id
        self.client = get_client()
        self.system_prompt = _montar_system_prompt()

    def responder(self, mensagem_usuario: str) -> str:
        mensagens = history.carregar_sessao(self.sessao_id)
        mensagens.append({"role": "user", "content": mensagem_usuario})
        indice_inicio = len(mensagens) - 1  # a partir daqui tudo é novo nesta rodada

        resposta_final = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            resposta = criar_mensagem(
                self.client,
                model=config.ANTHROPIC_MODEL,
                max_tokens=2048,
                system=self.system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=mensagens,
                output_config={"effort": "low"},
            )

            conteudo_serializado = [_serializar_bloco(b) for b in resposta.content]
            mensagens.append({"role": "assistant", "content": conteudo_serializado})

            if resposta.stop_reason != "tool_use":
                resposta_final = next(
                    (b.text for b in resposta.content if b.type == "text"), ""
                )
                break

            tool_use_blocks = [b for b in resposta.content if b.type == "tool_use"]
            resultados = []
            for bloco in tool_use_blocks:
                resultado = _executar_tool(bloco.name, bloco.input)
                resultados.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": bloco.id,
                        "content": resultado,
                    }
                )
            mensagens.append({"role": "user", "content": resultados})
        else:
            resposta_final = (
                "Desculpa, não consegui concluir essa consulta agora. "
                "Vou chamar um atendente humano pra te ajudar."
            )

        for msg in mensagens[indice_inicio:]:
            history.salvar_mensagem(self.sessao_id, msg["role"], msg["content"])

        return resposta_final
