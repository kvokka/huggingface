FROM python:3.11-slim

RUN pip install --no-cache-dir fastapi==0.131.0 uvicorn==0.41.0 httpx==0.28.1 && \
  useradd -m -u 1000 user

USER user

ENV HOME=/home/user
WORKDIR $HOME/app

COPY --chown=user main.py .

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
