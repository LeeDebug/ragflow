## 启动命令

   ```bash
   $ cd docker
   # 启动 cpu 版本？
   $ docker compose -p ragflow-cpu -f docker-compose.yml up -d
   # 启动 GPU 版本？
   $ docker compose -p ragflow-gpu -f docker-compose-gpu.yml up -d
   $ docker compose -p ragflow-gpu -f docker-compose-gpu.yml down
   ```