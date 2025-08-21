# chatbot-services
For Quantori

# How to launch it
You need to:
1. Install all dependencies
2. Install fasttext small model
3. Run the following containers:
- docker run -d --name vdb_container -e POSTGRES_USER=chatbot_base -e POSTGRES_PASSWORD=chatbot_base -e POSTGRES_DB=chatbot_base -p 6024:5432 postgres
- docker run -d --name redis_container -p 6379:6379 redis
5. Create .env file with variables
- VDB_CONN
- REDIS_CONN
- OPENAI_KEY
- SECRET_KEY=1234
- DEBUG=True
6. Inside app directory run "uvicorn main:app --reload" command
