import { getProcessedFileDownloadUrl } from "../api/files";

interface ProcessedDownloadLinkProps {
  processedFileId?: string;
}

export default function ProcessedDownloadLink({ processedFileId }: ProcessedDownloadLinkProps) {
  if (!processedFileId) {
    return null;
  }

  return (
    <a
      className="download-link"
      href={getProcessedFileDownloadUrl(processedFileId)}
      download={`${processedFileId}.csv`}
    >
      Download CSV
    </a>
  );
}
