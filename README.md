## Running locally
1. Obtain a copy of the `.env` file and place it in the root of the project

2. Build docker image
`docker build -t moveus:latest .`

3. Run docker container
`docker run -p 8000:8000 --env-file .env moveus`

4. Server is now running on `localhost:8000`
