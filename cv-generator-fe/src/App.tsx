import { CvChat } from "./components/cvChat";
import { CvPdfPane } from "./components/cvPdfPane";
import { resetChat } from "./features/cvGeneration/cvGenerationSlice";
import { useAppDispatch, useAppSelector } from "./hooks";

function App() {
  const dispatch = useAppDispatch();
  const { conversationId, messageHistory, latestPdfBase64 } = useAppSelector(
    (s) => s.cvGeneration,
  );
  const started = Boolean(conversationId) || messageHistory.length > 0;
  const showPdf = Boolean(latestPdfBase64);

  return (
    <main className={`app${showPdf ? " app-wide" : ""}`}>
      <header className="app-header">
        <h1>CV Generator</h1>
        <p>Chat with the assistant to refine your CV for a specific job.</p>
        {started ? (
          <button type="button" className="app-header-reset" onClick={() => dispatch(resetChat())}>
            New chat
          </button>
        ) : null}
      </header>

      <section className={`panel${showPdf ? " panel-with-pdf" : ""}`}>
        <CvChat />
        {showPdf ? <CvPdfPane base64={latestPdfBase64!} /> : null}
      </section>
    </main>
  );
}

export default App;
