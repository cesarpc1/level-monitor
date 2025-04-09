import asyncio
import httpx
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = "8012126560:AAGKMQUaOWOQRkL_4K2vj2gTNtlnoiYOk1M"
TELEGRAM_CHAT_ID = "5073217115"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
url_base = "https://api.level.money/v1/xp/balances/leaderboard?page={}&take=100"

valores_coletados = []

# Configuração inicial
inicio_coleta = datetime.now()
DIAS_PROJECAO = 49  # O número de dias de projeção total
CHECAGENS_POR_DIA = 24 * 60 * 2  # 30s

# 28 de maio às 00:00 como data de término da contagem
data_termino = datetime(2025, 5, 28, 0, 0)

# Limite mínimo para média por checagem
LIMIT_MINIMO_MEDIA = 100000  # Ajuste conforme necessário

async def fetch_pagina(client, pagina):
    url = url_base.format(pagina)
    try:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        usuarios = dados.get("leaderboard", [])
        return sum(
            int(item["balance"]["accrued"])
            for item in usuarios
            if "balance" in item and "accrued" in item["balance"]
        )
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

        if len(valores_coletados) >= 2:
            diferencas = [
                valores_coletados[i] - valores_coletados[i - 1]
                for i in range(1, len(valores_coletados))
            ]
            media_por_coleta = sum(diferencas) / len(diferencas)
        else:
            media_por_coleta = 0

        # Corrige a média caso seja muito pequena
        if media_por_coleta < LIMIT_MINIMO_MEDIA:
            media_por_coleta = LIMIT_MINIMO_MEDIA

        # Cálculo dinâmico de dias restantes até 28 de maio
        dias_restantes = max(0, (data_termino - datetime.now()).days)
        total_coletas_restantes = dias_restantes * CHECAGENS_POR_DIA

        # Projeção com base no valor atual + média x número de coletas restantes
        projecao_ajustada = int(total_atual + (media_por_coleta * total_coletas_restantes))

        # Garante que a projeção nunca seja negativa
        if projecao_ajustada < 0:
            projecao_ajustada = 0

        mensagem = (
            f"📊 Total atual de pontos: {total_atual:,}\n"
            f"📈 Média por checagem: {int(media_por_coleta):,}\n"
            f"🧮 Projeção para os próximos {dias_restantes} dias (até {data_termino.strftime('%d/%m/%Y')}): {projecao_ajustada:,} pontos"
        )

        print(mensagem)
        await enviar_telegram(mensagem)
        await asyncio.sleep(60)  # Executa a cada 60 segundos

asyncio.run(main_loop())
