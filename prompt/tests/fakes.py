class ScriptedClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, temperature):
        self.calls.append({"messages": list(messages), "temperature": temperature})
        if not self.replies:
            raise RuntimeError("no scripted replies left")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
