# psu-where-i-am
Расширение для interactions.py для парсинга списка поступающих в ПГНИУ (ПГУ)

## Как это выглядит:

![image](https://user-images.githubusercontent.com/25762802/182011732-7ffb53a5-94fa-4c96-8c0b-dde2a8733e2c.png)

## Установка
`pip install -r requirements.txt`

## Настройка
1. Создайте файл `.env`
2. Установите следующие переменные:

```
TOKEN= Токен бота
SNILS= Ваш СНИЛС
SITE_URL= Текущий сайт с списком поступающих
WEBHOOK_URL= Ссылка вебхука
DISCORD_USER_ID= Ваш id в дискорде (Необязательно)
EMOJI_ARROW_DOWN= Эмодзи (Необязательно)
EMOJI_ARROW_UP= Эмодзи (Необязательно)
```

3. Запустите бота через файл `main.py`
