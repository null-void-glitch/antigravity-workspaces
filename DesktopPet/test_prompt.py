from prompt_toolkit import PromptSession
from rich.prompt import Prompt

session = PromptSession()
line = session.prompt("type something: ")
print("you typed:", line)

pw = Prompt.ask("API key", password=True)
print("pw:", pw)
