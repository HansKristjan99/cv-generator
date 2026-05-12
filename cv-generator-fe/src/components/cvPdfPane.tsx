export const CvPdfPane = ({ base64 }: { base64: string }) => {
  const dataUrl = `data:application/pdf;base64,${base64}`;
  return (
    <aside className="cv-pdf-pane">
      <div className="cv-pdf-pane-header">
        <h2>PDF preview</h2>
        <a className="cv-pdf-pane-download" href={dataUrl} download="cv.pdf">
          Download
        </a>
      </div>
      <iframe className="cv-pdf-pane-frame" src={dataUrl} title="Rendered CV" />
    </aside>
  );
};
