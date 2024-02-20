
## Step 1: Instal dependencies
```
pip install -r requirements.txt
```

## Step 2: Add API KEY in code
`helper.py: line 16` - Key of gemini llm
```
GOOGLE_API_KEY="AIzaSyBRc0cacOVzHcoyqBUI-_Q_7wbHbuvy7VY"
```

`config.py: line 2` - Key of telebot
```
TOKEN = "6740442101:AAH4FTUwE1i1sLJ2EtidSaO3sK6HqHTmg1A"
```

## Step 3: Run Backend for Telebot to start conversation
```
python bot.py
```

- In telebot on telegram, input `\start` for starting conversation

- When select a ticker, the bot will automatically questions default 3 questions and answer them, so it may take some time untill finished run.