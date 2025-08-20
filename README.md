# chatbot-services
For Quantori

# How to launch it
You need to:
1. Install all dependencies
2. Install fasttext small model
3. Run the following containers:
docker run -d --name vdb_container -e POSTGRES_USER=chatbot_base -e POSTGRES_PASSWORD=chatbot_base -e POSTGRES_DB=chatbot_base -p 6024:5432 postgres
docker run -d --name redis_container -p 6379:6379 redis
4. Create .env file with variables
