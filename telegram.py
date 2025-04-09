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

# Função para buscar a posição desejada (72, 68 ou 85)
async def buscar_posicao_desejada(client, posicao_desejada):
    url = url_base.format(1)
    try:
        resposta = await client.get(url)
        resposta.raise_for_status()
        dados = resposta.json()
        usuarios = dados.get("leaderboard", [])
        
        if len(usuarios) >= posicao_desejada:
            usuario = usuarios[posicao_desejada - 1]  # Ajustando índice para 1-based
            return {
                "pontos": int(usuario["balance"]["accrued"]) if "balance" in usuario and "accrued" in usuario["balance"] else 0,
                "posicao": posicao_desejada
            }
        else:
            return {"pontos": 0, "posicao": None}
    except Exception as e:
        print(f"❌ Erro ao buscar a posição {posicao_desejada}: {e}")
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

# Função para trackear a posição 72 (ou 68 ou 85)
async def trackear_posicao():
    posicao_atual = 72
    previous_pontos = 0  # Armazenar os pontos da posição anterior
    while True:
        async with httpx.AsyncClient() as client:
            resultado = await buscar_posicao_desejada(client, posicao_atual)
            pontos_posicao = resultado["pontos"]
            posicao = resultado["posicao"]
            
            # Caso a posição mude para 68 ou 85, alteramos o tracking
            if posicao in [68, 85]:
                posicao_atual = posicao

            # Calcular o incremento de pontos nos últimos 5 minutos
            if previous_pontos != 0:
                incremento_5minutos = pontos_posicao - previous_pontos
            else:
                incremento_5minutos = 0

            # Projeção dos pontos para os próximos 48 dias
            projeção_48_dias = pontos_posicao + (incremento_5minutos * TOTAL_MINUTOS_RESTANTES)

            # Montar a mensagem
            mensagem = (
                f"📊 **Pontos da posição {posicao_atual} do leaderboard**: {pontos_posicao:,}\n"
                f"📍 **Posição Atual**: {posicao} \n"
                f"🕒 **Incremento nos últimos 5 minutos**: {incremento_5minutos:,} pontos\n"
                f"🧮 **Projeção para os próximos 48 dias**: {int(projeção_48_dias):,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_pontos = pontos_posicao  # Atualizar os pontos para a próxima checagem
            await asyncio.sleep(300)  # A cada 5 minutos (300 segundos)

# Função principal para rodar o loop
async def main_loop():
    previous_total = 0  # Armazenar o total da checagem anterior
    while True:
        async with httpx.AsyncClient() as client:
            # Calcular pontos totais no leaderboard
            total_atual = await calcular_total()

            # Calcular o incremento total do leaderboard nos últimos 30 segundos
            if previous_total != 0:
                incremento_30segundos_total = total_atual - previous_total
            else:
                incremento_30segundos_total = 0

            # Projeção total do leaderboard para os próximos 48 dias
            projeção_48_dias_total = total_atual + (incremento_30segundos_total * TOTAL_MINUTOS_RESTANTES)

            # Montar a mensagem
            mensagem = (
                f"📊 **Total atual de pontos do leaderboard**: {total_atual:,}\n"
                f"🕒 **Incremento nos últimos 30 segundos**: {incremento_30segundos_total:,} pontos\n"
                f"🧮 **Projeção total do leaderboard para os próximos 48 dias**: {int(projeção_48_dias_total):,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_total = total_atual  # Atualizar o total para a próxima checagem
            await asyncio.sleep(30)  # A cada 30 segundos (30 segundos)

# Rodar as funções em paralelo
async def run():
    # Inicia o trackeamento da posição 72 (ou 68 ou 85) e do leaderboard
    task1 = asyncio.create_task(main_loop())
    task2 = asyncio.create_task(trackear_posicao())
    await asyncio.gather(task1, task2)

asyncio.run(run())
