import ChatWindow from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-950 p-4 transition-colors duration-200">
      <div className="w-full max-w-2xl h-[85vh] flex flex-col rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shadow-2xl overflow-hidden transition-colors duration-200">
        <ChatWindow />
      </div>
    </main>
  );
}
