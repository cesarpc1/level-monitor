import asyncio
import httpx

TELEGRAM_BOT_TOKEN = "8012126560:AAGKMQUaOWOQRkL_4K2vj2gTNtlnoiYOk1M"
TELEGRAM_CHAT_ID = "5073217115"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
url_base = "https://api.level.money/v1/xp/balances/leaderboard?page={}&take=100"

valores_coletados = []

# 49 dias * 24h * 60min * 2 checagens por min (a cada 30s)
TOTAL_COLETAS_49_DIAS = (49 * 24 * 60 * 2)

# Definir as variáveis de contagem dos dias restantes
dias_restantes = 48  # Dias restantes para a projeção (até 28/05/2025)
TOTAL_COLETAS_RESTANTES = dias_restantes * 24 * 60 * 2  # 2 checagens por minuto, 60 minutos por hora, 24 horas por dia

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

async def calcular_total():
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        resp = await client.get(url_base.format(1))
        resp.raise_for_status()
        dados = resp.json()
        total_pages = dados.get("totalPages", 1)

        tasks = [fetch_pagina(client, i) for i in range(1, total_pages + 1)]
        resultados = await asyncio.gather(*tasks)
        return sum(resultados)

async def main_loop():
    while True:
        total_atual = await calcular_total()
        valores_coletados.append(total_atual)

        # Projeção de crescimento
        projeção_49_dias = int(total_atual + (total_atual * TOTAL_COLETAS_RESTANTES))

        mensagem = (
            f"📊 Total atual de pontos: {total_atual:,}\n"
            f"🧮 Projeção para os próximos {dias_restantes} dias (até 28/05/2025): {projeção_49_dias:,} pontos"
        )

        print(mensagem)
        await enviar_telegram(mensagem)
        await asyncio.sleep(60)  # A cada 60 segundos

asyncio.run(main_loop())
