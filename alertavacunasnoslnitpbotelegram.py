import ccxt
import time
import pandas as pd
from datetime import datetime
import requests  # Para enviar mensajes a Telegram

# Configura el exchange (en este caso, Binance)
exchange = ccxt.binance()

# Lista de criptomonedas a analizar
symbols = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "TRX/USDT", "TON/USDT", "ADA/USDT", "AVAX/USDT", 
    "SHIB/USDT", "LINK/USDT", "BCH/USDT", "DOT/USDT", "NEAR/USDT", "SUI/USDT", "LTC/USDT", "APT/USDT", "TAO/USDT", "UNI/USDT", 
    "PEPE/USDT", "ICP/USDT", "FET/USDT", "KAS/USDT", "POL/USDT", "RENDER/USDT", "ETC/USDT", "XLM/USDT", "STX/USDT", "WIF/USDT", 
    "IMX/USDT", "FIL/USDT", "AAVE/USDT", "OP/USDT", "HBAR/USDT", "ARB/USDT", "INJ/USDT", "VET/USDT", "ATOM/USDT", "RUNE/USDT",
    "GRT/USDT", "SEI/USDT", "BONK/USDT", "FLOKI/USDT", "THETA/USDT", "AR/USDT", "MKR/USDT", "POPCAT/USDT", "OM/USDT", "HNT/USDT", 
    "PYTH/USDT", "TIA/USDT", "ALGO/USDT", "JUP/USDT", "LDO/USDT", "WLD/USDT", "ONDO/USDT", "JASMY/USDT", "BSV/USDT", "BTT/USDT", 
    "BRETT/USDT", "CFX/USDT", "FLOW/USDT", "QNT/USDT", "W/USDT", "NOT/USDT", "ENA/USDT", "STRK/USDT", "FTT/USDT", "EIGEN/USDT", 
    "ORDI/USDT", "NEO/USDT", "EOS/USDT", "EGLD/USDT", "NEIRO/USDT", "AXS/USDT", "CKB/USDT", "XEC/USDT", "XTZ/USDT", "PENDLE/USDT", 
    "CHZ/USDT", "MINA/USDT", "AKT/USDT", "SAND/USDT", "DYDX/USDT", "MEW/USDT", "ENS/USDT", "MANA/USDT", "SUPER/USDT", "CAKE/USDT", 
    "LUNC/USDT", "ROSE/USDT", "DEXE/USDT", "ZK/USDT", "SNX/USDT", "RAY/USDT", "ZRO/USDT", "BOME/USDT", "APE/USDT", "BLUR/USDT", 
    "ASTR/USDT", "SAFE/USDT", "TWT/USDT", "IOTA/USDT", "LPT/USDT", "TFUEL/USDT", "COMP/USDT", "CELO/USDT", "PEOPLE/USDT", "ETHW/USDT", 
    "DOGS/USDT", "GMT/USDT", "KAVA/USDT", "OSMO/USDT"
]

# Configuración del bot de Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Reemplaza con tu token de bot
TELEGRAM_CHAT_ID = '-1002402110104'  # Reemplaza con tu chat ID

# Función para enviar mensajes a Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Error al enviar mensaje a Telegram: {response.text}")

# Función para obtener datos OHLCV (Open, High, Low, Close, Volume)
def get_ohlcv(symbol, timeframe='5m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Función para calcular el MACD
def calculate_macd(df, short_window=12, long_window=26, signal_window=9):
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
    df['macd_line'] = df['ema_short'] - df['ema_long']
    df['signal_line'] = df['macd_line'].ewm(span=signal_window, adjust=False).mean()
    return df

# Función para identificar martillo y hombre colgado
def identify_signals(df):
    df['body_size'] = abs(df['close'] - df['open'])
    df['total_size'] = df['high'] - df['low']
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    
    df['is_hammer'] = (df['lower_shadow'] >= 2 * df['body_size']) & (df['upper_shadow'] <= df['body_size'])
    df['is_hanging_man'] = (df['upper_shadow'] >= 2 * df['body_size']) & (df['lower_shadow'] <= df['body_size'])
    
    df['filter_size'] = df['total_size'] >= 3 * df['body_size']
    
    # Filtro de volumen: SMA de 10 períodos
    df['volume_sma'] = df['volume'].rolling(window=10).mean()
    
    # Filtro de apertura y cierre de las 4 velas anteriores
    df['filter_hanging_man'] = True  # Hombre colgado: apertura y cierre mayores que los de las 4 velas anteriores
    df['filter_hammer'] = True       # Martillo: apertura y cierre menores que los de las 4 velas anteriores
    
    for i in range(1, 5):  # Evaluar las 4 velas anteriores
        df['filter_hanging_man'] &= (df['open'] > df['open'].shift(i)) & (df['close'] > df['close'].shift(i))
        df['filter_hammer'] &= (df['open'] < df['open'].shift(i)) & (df['close'] < df['close'].shift(i))
    
    # Aplicar todos los filtros
    df['show_hammer'] = df['is_hammer'] & (df['macd_line'] < df['signal_line']) & (df['volume'] > df['volume_sma']) & df['filter_size'] & df['filter_hammer']
    df['show_hanging_man'] = df['is_hanging_man'] & (df['macd_line'] > df['signal_line']) & (df['volume'] > df['volume_sma']) & df['filter_size'] & df['filter_hanging_man']
    
    return df

# Función principal para monitorear las criptomonedas
def monitor_cryptos():
    print("Iniciando monitoreo de criptomonedas...")
    last_signals = {symbol: None for symbol in symbols}  # Almacena la última señal detectada para evitar repeticiones
    
    while True:
        alerts = []  # Lista para almacenar las alertas del ciclo actual
        
        for symbol in symbols:
            try:
                df = get_ohlcv(symbol, timeframe='5m')  # Intervalo de 5 minutos
                df = calculate_macd(df)
                df = identify_signals(df)
                
                # Evaluar la vela anterior (la que ya ha cerrado)
                if len(df) >= 2:  # Asegurarse de que hay al menos 2 velas
                    previous_candle = df.iloc[-2]  # Vela anterior
                    current_time = df.iloc[-1]['timestamp']  # Tiempo de la vela actual
                    
                    if previous_candle['show_hammer'] and last_signals[symbol] != 'hammer':
                        alert_message = f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] {symbol} ha sido vacunado: Reversión Alcista 🟢"
                        alerts.append(alert_message)
                        last_signals[symbol] = 'hammer'  # Registrar la señal
                    
                    if previous_candle['show_hanging_man'] and last_signals[symbol] != 'hanging_man':
                        alert_message = f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] {symbol} ha sido vacunado: Reversión Bajista 🔴"
                        alerts.append(alert_message)
                        last_signals[symbol] = 'hanging_man'  # Registrar la señal
            except Exception as e:
                print(f"Error al procesar {symbol}: {e}")
        
        # Enviar todas las alertas juntas por Telegram
        if alerts:
            message = "\n".join(alerts)
            print(message)  # Mostrar alertas en la consola
            send_telegram_message(message)  # Enviar alertas por Telegram
        
        time.sleep(300)  # Espera 1 minuto antes de la siguiente iteración

# Ejecutar el monitor
monitor_cryptos()
