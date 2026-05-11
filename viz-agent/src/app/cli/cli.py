import uuid

from langchain_core.messages import HumanMessage

from app.bootstrap import build_runtime


runtime = build_runtime()

thread_id = str(uuid.uuid4())

config = {"configurable": {"thread_id": thread_id}}


def chat():
    print("Viz Agent ready. Type 'exit' to quit.")

    while True:
        user = input("You: ").strip()

        if not user:
            continue

        if user.lower() == "exit":
            break

        state = {"messages": [HumanMessage(content=user)]}

        result = runtime.invoke(state, config=config)

        print(f"Agent: {result['messages'][-1].content}")


if __name__ == "__main__":
    chat()
