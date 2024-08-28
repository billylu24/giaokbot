import discord
import requests
from flask import Flask, request, jsonify
import subprocess
from pyngrok import ngrok
import atexit
import signal
import os
import threading

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化 Discord 客户端
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 定义一个路由来处理API请求
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('input')

    # 调用 Ollama 模型，通过命令行运行并捕获输出
    process = subprocess.Popen(
        ['ollama', 'run', 'llama3'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate(input=user_input.encode('utf-8'))

    if process.returncode == 0:
        # 处理模型返回的结果
        model_response = stdout.decode('utf-8').strip()
        return jsonify({"response": model_response})
    else:
        return jsonify({"error": stderr.decode('utf-8')}), 500

# 清理函数，当 Flask 停止时调用
def cleanup():
    print("Stopping Ngrok and any running subprocesses...")
    ngrok.disconnect(public_url)
    ngrok.kill()

atexit.register(cleanup)

# Discord 事件处理
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    # 忽略机器人自身的消息
    if message.author == client.user:
        return

    print(f"Received message: '{message.content}' from {message.author} in {message.channel}")

    # 当消息以 !giaok 开头时，发送请求到 Flask API
    if message.content.startswith('!giaok'):
        user_input = message.content[len('!giaok '):].strip()
        print(f"User input extracted: '{user_input}'")

        # 发送请求到 Flask API
        try:
            response = requests.post(str(public_url) + "/api/chat", json={"input": user_input})
            print(f"API response status code: {response.status_code}")
            print(f"API response content: {response.content}")

            if response.status_code == 200:
                data = response.json()
                reply = data.get('response', 'Sorry, I did not understand that.')
            else:
                reply = f"Error: Could not process your request. Status code: {response.status_code}"
        except Exception as e:
            reply = f"An error occurred: {str(e)}"
            print(f"Exception occurred: {str(e)}")

        await message.channel.send(reply)

if __name__ == '__main__':
    # 启动 Flask 应用
    port = 5000
    public_url = ngrok.connect(port).public_url
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")

    # 设置信号处理器以在接收到终止信号时调用清理函数
    signal.signal(signal.SIGINT, lambda s, f: os._exit(0))

    # 启动 Discord 机器人
    threading.Thread(target=lambda: client.run('your code')).start()

    # 启动 Flask 服务
    app.run(host='0.0.0.0', port=port)
