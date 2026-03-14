import { useEffect, useRef, useState } from "react";
import { getApiBase } from "../api/client";
import "./FlutterScannerEmbed.css";

/**
 * Embeds the Flutter scanner app (results table + Validate AI) in an iframe.
 * Passes jobId, apiBase, and auth token via postMessage after load.
 * @param {boolean} fillHeight - If true, iframe fills the parent (for full-screen page).
 */
const MIN_EMBED_HEIGHT = 400;
const MAX_EMBED_HEIGHT = 2000;

export default function FlutterScannerEmbed({ jobId, token, fillHeight = false }) {
  const iframeRef = useRef(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [embedHeight, setEmbedHeight] = useState(MIN_EMBED_HEIGHT);

  useEffect(() => {
    const handleMessage = (event) => {
      if (event.source !== iframeRef.current?.contentWindow) return;
      try {
        const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (data?.type === "resize" && typeof data.height === "number") {
          const h = Math.min(MAX_EMBED_HEIGHT, Math.max(MIN_EMBED_HEIGHT, data.height));
          setEmbedHeight(h);
        }
      } catch {
        // ignore
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  useEffect(() => {
    setIframeLoaded(false);
    setEmbedHeight(MIN_EMBED_HEIGHT);
    const iframe = iframeRef.current;
    if (!iframe || !jobId) return;

    const sendConfig = () => {
      const apiBase = getApiBase();
      try {
        const payload = JSON.stringify({
          jobId,
          apiBase,
          token: token ?? null,
        });
        iframe.contentWindow?.postMessage(payload, window.location.origin);
      } catch {
        // ignore
      }
    };

    let retryTimeout;
    const onLoad = () => {
      sendConfig();
      setIframeLoaded(true);
      retryTimeout = setTimeout(sendConfig, 200);
    };

    iframe.addEventListener("load", onLoad);
    return () => {
      iframe.removeEventListener("load", onLoad);
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [jobId, token]);

  if (!jobId) return null;

  const apiBase = getApiBase();
  const src = `/flutter-scanner/index.html?jobId=${encodeURIComponent(jobId)}&apiBase=${encodeURIComponent(apiBase)}`;

  const iframeStyle = fillHeight
    ? { minHeight: "100%", height: "100%" }
    : { minHeight: embedHeight, height: embedHeight };

  return (
    <div className={`flutter-scanner-embed${fillHeight ? " flutter-scanner-embed--fill" : ""}`}>
      {!iframeLoaded && (
        <div className="flutter-scanner-embed__loading" aria-live="polite">
          Loading results…
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={src}
        title="Statement results and Validate AI"
        className="flutter-scanner-embed__iframe"
        style={iframeStyle}
      />
    </div>
  );
}
