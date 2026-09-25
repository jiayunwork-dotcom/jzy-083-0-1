"""服务入口：python run.py，监听 0.0.0.0:8080，多线程并发。"""
from app.server import create_app

app = create_app()

if __name__ == "__main__":
    # threaded=True：多路请求并发处理；计算无共享状态，各路互不影响
    app.run(host="0.0.0.0", port=8080, threaded=True)
