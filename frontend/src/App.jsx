import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Loader from "./components/Loader";
import SummaryTable from "./components/SummaryTable";
import ResultsTable from "./components/ResultsTable";
import ChatPanel from "./components/ChatPanel";
import { processPdf } from "./api/client";
import "./App.css";

function App() {
  const [jobId, setJobId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [summaryByCategory, setSummaryByCategory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingFile, setLoadingFile] = useState(null);
  const [error, setError] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const handleUpload = async (file) => {
    setError(null);
    setDownloadError(null);
    setLoading(true);
    setLoadingFile({ name: file.name, size: file.size });
    try {
      const data = await processPdf(file);
      setJobId(data.job_id);
      setTransactions(data.transactions || []);
      setSummaryByCategory(data.summary_by_category || []);
    } catch (e) {
      setError(e.message || "Upload failed");
      setJobId(null);
      setTransactions([]);
      setSummaryByCategory([]);
    } finally {
      setLoading(false);
      setLoadingFile(null);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Bank Statement Processor</h1>
        <p>Upload a PDF statement to itemize and categorize transactions, then validate with the chatbot.</p>
      </header>

      <main className="app-main">
        <FileUpload onUpload={handleUpload} disabled={loading} />
        {loading && (
          <Loader
            fileName={loadingFile?.name}
            fileSize={loadingFile?.size}
          />
        )}
        {error && <p className="status error">{error}</p>}
        {downloadError && <p className="status error">{downloadError}</p>}

        <SummaryTable summaryByCategory={summaryByCategory} />
        <ResultsTable
          transactions={transactions}
          jobId={jobId}
          onDownloadError={setDownloadError}
        />

        <ChatPanel jobId={jobId} disabled={!jobId} />
      </main>
    </div>
  );
}

export default App;
