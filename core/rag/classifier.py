ASTRO_TOPICS = {

    "love": [
        "любов",
        "брак",
        "отношен",
        "развод",
        "совместим",
        "синастр"
    ],

    "money": [
        "работ",
        "карьер",
        "бизнес",
        "деньг",
        "финанс"
    ],

    "health": [
        "болезн",
        "здоров",
        "орган",
        "энерг"
    ],

    "spirit": [
        "карма",
        "душ",
        "предназнач",
        "духов"
    ]
}


def classify_question(text: str):

    text = text.lower()

    for topic, words in ASTRO_TOPICS.items():

        for word in words:

            if word in text:

                return topic

    return "general"