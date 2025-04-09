import asyncio
import httpx

TELEGRAM_BOT_TOKEN = "8012126560:AAGKMQUaOWOQRkL_4K2vj2gTNtlnoiYOk1M"
TELEGRAM_CHAT_ID = "5073217115"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

url_base = "https://api.level.money/v1/xp/balances/leaderboard?page={}&take=100"

# 48 dias restantes * 24h * 60min
TOTAL_MINUTOS_RESTANTES = 48 * 24 * 60  # Número total de minutos restantes (48 dias em minutos)

# Função para buscar a posição 72 do leaderboard
async def buscar_posicao_72(client):
    url = url_base.format(1)
    try:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        usuarios = dados.get("leaderboard", [])
        
        # Verifica se há usuários suficientes na lista
        if len(usuarios) >= 72:
            usuario_72 = usuarios[71]  # Posição 72 (índice 71)
            return {
                "pontos": int(usuario_72["balance"]["accrued"]) if "balance" in usuario_72 and "accrued" in usuario_72["balance"] else 0,
                "posicao": 72
            }
        else:
            return {"pontos": 0, "posicao": None}
    except Exception as e:
        print(f"❌ Erro ao buscar a posição 72: {e}")
        return {"pontos": 0, "posicao": None}

# Função para calcular o total de pontos do leaderboard
async def calcular_total():
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        resp = await client.get(url_base.format(1))
        resp.raise_for_status()
        dados = resp.json()
        total_pages = dados.get("totalPages", 1)

        tasks = [fetch_pagina(client, i) for i in range(1, total_pages + 1)]
        resultados = await asyncio.gather(*tasks)
        return sum(resultados)

async def fetch_pagina(client, pagina):
    url = url_base.format(pagina)
    try:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        usuarios = dados.get("leaderboard", [])
        return sum(int(item["balance"]["accrued"]) for item in usuarios if "balance" in item and "accrued" in item["balance"])
    except Exception as e:
        print(f"❌ Erro na página {pagina}: {e}")
        return 0

async def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, data=payload)
        except Exception as e:
            print(f"❌ Erro ao enviar para Telegram: {e}")

async def main_loop():
    previous_pontos_72 = 0  # Armazenar os pontos da posição 72 da checagem anterior
    previous_total = 0  # Armazenar o total da checagem anterior
    while True:
        async with httpx.AsyncClient() as client:
            # Buscar a posição 72 do leaderboard
            resultado_72 = await buscar_posicao_72(client)
            pontos_posicao_72 = resultado_72["pontos"]
            posicao_72 = resultado_72["posicao"]

            # Calcular pontos totais no leaderboard
            total_atual = await calcular_total()

            # Calcular a diferença de pontos da posição 72 e o incremento de pontos
            if previous_pontos_72 != 0:
                incremento_10minutos_72 = pontos_posicao_72 - previous_pontos_72
            else:
                incremento_10minutos_72 = 0

            # Projeção para os próximos 48 dias em minutos (posição 72)
            projeção_48_dias_72 = pontos_posicao_72 + (incremento_10minutos_72 * TOTAL_MINUTOS_RESTANTES)

            # Calcular o incremento total do leaderboard nos últimos 10 minutos
            if previous_total != 0:
                incremento_10minutos_total = total_atual - previous_total
            else:
                incremento_10minutos_total = 0

            # Projeção total do leaderboard para os próximos 48 dias
            projeção_48_dias_total = total_atual + (incremento_10minutos_total * TOTAL_MINUTOS_RESTANTES)

            # Verificar se a posição mudou (subiu ou desceu)
            posicao_mudou = ""
            if posicao_72 is not None:
                if previous_total != 0:
                    if posicao_72 < previous_total:
                        posicao_mudou = "↑"
                    elif posicao_72 > previous_total:
                        posicao_mudou = "↓"
                previous_total = posicao_72

            # Montar a mensagem
            mensagem = (
                f"📊 **Pontos da posição 72 do leaderboard**: {pontos_posicao_72:,}\n"
                f"📍 **Posição Atual**: {posicao_72} {posicao_mudou}\n"
                f"🕒 **Pontos ganhados nos últimos 10 minutos (posição 72)**: {incremento_10minutos_72:,} pontos\n"
                f"📊 **Total atual de pontos do leaderboard**: {total_atual:,}\n"
                f"🧮 **Projeção para os próximos 48 dias (posição 72)**: {int(projeção_48_dias_72):,} pontos\n"
                f"🧮 **Projeção total do leaderboard para os próximos 48 dias**: {int(projeção_48_dias_total):,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_pontos_72 = pontos_posicao_72  # Atualizar os pontos da posição 72 para a próxima checagem
            await asyncio.sleep(600)  # A cada 10 minutos (600 segundos)

asyncio.run(main_loop())
