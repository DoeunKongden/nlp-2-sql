def convert_to_plain_language(result):
    if not result:
        return "I couldn't find any relevent information."
    response = "Here are the result"
    for row in result:
        row_text = ", ".join(f"{key}: {value}" for key, value in row.items())
        response += f"\n- {row_text}"
    return response
