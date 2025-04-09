import asyncio
import httpx

TELEGRAM_BOT_TOKEN = "8012126560:AAGKMQUaOWOQRkL_4K2vj2gTNtlnoiYOk1M"
TELEGRAM_CHAT_ID = "5073217115"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Sua carteira específica
CARTEIRA_ENDERECO = "0x4cc929294C49434B59ECa0aA96653dA49aC2b10e"

url_base = "https://api.level.money/v1/xp/balances/leaderboard?page={}&take=100"

valores_coletados = []

# 48 dias restantes * 24h * 60min
TOTAL_MINUTOS_RESTANTES = 48 * 24 * 60  # Número total de minutos restantes (48 dias em minutos)

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

# Função para buscar os pontos específicos da sua carteira
async def buscar_pontos_carteira(client, endereco_carteira):
    url = f"https://api.level.money/v1/xp/balances/{endereco_carteira}"
    try:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        return int(dados.get("balance", 0))  # Retorna os pontos da carteira
    except Exception as e:
        print(f"❌ Erro ao buscar pontos da carteira {endereco_carteira}: {e}")
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
    previous_total = 0  # Armazenar o total da checagem anterior
    while True:
        async with httpx.AsyncClient() as client:
            # Buscar pontos da sua carteira
            pontos_carteira = await buscar_pontos_carteira(client, CARTEIRA_ENDERECO)

            # Calcular pontos totais no leaderboard
            total_atual = await calcular_total()
            valores_coletados.append(total_atual)

            # Calcular a diferença de pontos entre a checagem atual e a anterior
            if previous_total != 0:
                incremento_por_minuto = total_atual - previous_total
            else:
                incremento_por_minuto = 0

            # Projeção para os próximos 48 dias em minutos
            projeção_48_dias = total_atual + (incremento_por_minuto * TOTAL_MINUTOS_RESTANTES)

            mensagem = (
                f"📊 **Total de pontos do seu endereço ({CARTEIRA_ENDERECO})**: {pontos_carteira:,}\n"
                f"📊 **Total atual de pontos do leaderboard**: {total_atual:,}\n"
                f"🧮 **Projeção para os próximos 48 dias (até 28/05/2025)**: {int(projeção_48_dias):,} pontos\n"
                f"⏱️ **Incremento a cada 10 minutos**: {incremento_por_minuto * 10:,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_total = total_atual  # Atualizar o total para a próxima checagem
            await asyncio.sleep(600)  # A cada 10 minutos (600 segundos)

asyncio.run(main_loop())
