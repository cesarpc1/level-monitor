import asyncio
import httpx
from datetime import datetime, date

TELEGRAM_BOT_TOKEN = "8012126560:AAGKMQUaOWOQRkL_4K2vj2gTNtlnoiYOk1M"
TELEGRAM_CHAT_ID = "5073217115"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

url_base = "https://api.level.money/v1/xp/balances/leaderboard?page={}&take=100"

# Data final para a projeção
END_DATE = date(2025, 8, 29)

# Função para calcular dias restantes até 29 de agosto de 2025
def get_remaining_days():
    today = date.today()
    delta = END_DATE - today
    return max(0, delta.days)  # Garante que não retorna negativo após a data

# Função para calcular minutos restantes até 29 de agosto de 2025
def get_remaining_minutes():
    return get_remaining_days() * 24 * 60  # Dias restantes * horas * minutos

# Função para buscar a posição desejada (67)
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

# Função para trackear a posição 67
async def trackear_posicao():
    posicao_fixa = 67  # Sempre trackear a posição 67
    previous_pontos = 0  # Armazenar os pontos da posição anterior
    while True:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            resultado = await buscar_posicao_desejada(client, posicao_fixa)
            pontos_posicao = resultado["pontos"]
            posicao = resultado["posicao"]
            
            # Calcular o incremento de pontos nos últimos 5 minutos
            incremento_5minutos = pontos_posicao - previous_pontos if previous_pontos != 0 else 0

            # Projeção dos pontos até 29 de agosto
            minutos_restantes = get_remaining_minutes()
            projeção = pontos_posicao + (incremento_5minutos * minutos_restantes)

            # Montar a mensagem
            mensagem = (
                f"📊 **Pontos da posição {posicao_fixa} do leaderboard**: {pontos_posicao:,}\n"
                f"📍 **Posição Atual**: {posicao}\n"
                f"🕒 **Incremento nos últimos 5 minutos**: {incremento_5minutos:,} pontos\n"
                f"📅 **Dias restantes até 29/08/2025**: {get_remaining_days()} dias\n"
                f"🧮 **Projeção até 29/08/2025**: {int(projeção):,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_pontos = pontos_posicao  # Atualizar os pontos para a próxima checagem
            await asyncio.sleep(300)  # A cada 5 minutos

# Função principal para rodar o loop do leaderboard
async def main_loop():
    previous_total = 0  # Armazenar o total da checagem anterior
    while True:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            # Calcular pontos totais no leaderboard
            total_atual = await calcular_total()

            # Calcular o incremento total do leaderboard nos últimos 30 segundos
            incremento_30segundos_total = total_atual - previous_total if previous_total != 0 else 0

            # Projeção total do leaderboard até 29 de agosto
            minutos_restantes = get_remaining_minutes()
            projeção_total = total_atual + (incremento_30segundos_total * minutos_restantes)

            # Montar a mensagem
            mensagem = (
                f"📊 **Total atual de pontos do leaderboard**: {total_atual:,}\n"
                f"🕒 **Incremento nos últimos 30 segundos**: {incremento_30segundos_total:,} pontos\n"
                f"📅 **Dias restantes até 29/08/2025**: {get_remaining_days()} dias\n"
                f"🧮 **Projeção total até 29/08/2025**: {int(projeção_total):,} pontos"
            )

            print(mensagem)
            await enviar_telegram(mensagem)

            previous_total = total_atual  # Atualizar o total para a próxima checagem
            await asyncio.sleep(30)  # A cada 30 segundos

# Rodar as funções em paralelo
async def run():
    task1 = asyncio.create_task(main_loop())
    task2 = asyncio.create_task(trackear_posicao())
    await asyncio.gather(task1, task2)

if __name__ == "__main__":
    asyncio.run(run())
