# Development plan

I will build the bot in small stages so that each stage is testable on the VM without relying on Telegram first. The first step is scaffolding: create a clear bot entry point, configuration loader, handler layer, and service layer. The handlers must stay independent from Telegram so they can be called both from a CLI test mode and from real Telegram updates. This reduces debugging time and makes the autochecker easier to satisfy.

The second step is backend integration. I will add a small LMS API client that talks to the backend using the base URL and API key from `.env.bot.secret`. Then I will implement `/health`, `/labs`, and later `/scores` using that client. Errors such as backend downtime or invalid responses should be caught and converted into friendly user messages instead of tracebacks.

The third step is natural language routing. I will add an LLM service that can classify user intent and decide which backend actions to call. The same service layer will later expose backend endpoints as tools so the bot can answer plain-language questions.

The final step is deployment. I will keep the bot runnable locally with `uv run bot.py --test ...`, then run it in Telegram mode on the VM, and later containerize it for the final task.
