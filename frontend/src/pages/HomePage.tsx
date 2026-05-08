import { useState } from "react";

import { uploadFile } from "../api/files";
import { applyReplacement, generateRegex } from "../api/regex";
import DataPreviewTable from "../components/DataPreviewTable";
import ErrorMessage from "../components/ErrorMessage";
import FileUploader from "../components/FileUploader";
import ProcessedDataTable from "../components/ProcessedDataTable";
import RegexGenerationPanel from "../components/RegexGenerationPanel";
import RegexPreviewCard from "../components/RegexPreviewCard";
import ReplacementPanel from "../components/ReplacementPanel";
import ReplacementStatsCard from "../components/ReplacementStatsCard";
import { FileUploadResponse, UploadApiError } from "../types/files";
import { RegexApiError, RegexGenerateResponse, RegexReplaceResponse } from "../types/regex";

export default function HomePage() {
  const [previewData, setPreviewData] = useState<FileUploadResponse | null>(null);
  const [regexResult, setRegexResult] = useState<RegexGenerateResponse | null>(null);
  const [replaceResult, setReplaceResult] = useState<RegexReplaceResponse | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [naturalLanguage, setNaturalLanguage] = useState("");
  const [replacementValue, setReplacementValue] = useState("REDACTED");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [replaceError, setReplaceError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [replaceLoading, setReplaceLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  async function handleUpload(file: File) {
    setIsUploading(true);
    setErrorMessage(null);
    setReplaceError(null);
    setRegexResult(null);
    setReplaceResult(null);
    setTargetColumn("");

    try {
      const response = await uploadFile(file);
      setPreviewData(response);
    } catch (error) {
      setPreviewData(null);
      setErrorMessage(errorToMessage(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleGenerateRegex() {
    if (!previewData) {
      setErrorMessage("Upload a CSV or XLSX file before generating a regex.");
      return;
    }

    if (!targetColumn) {
      setErrorMessage("Choose a target column before generating a regex.");
      return;
    }

    if (!naturalLanguage.trim()) {
      setErrorMessage("Describe the pattern you want to find.");
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    setReplaceError(null);
    setRegexResult(null);
    setReplaceResult(null);

    try {
      const response = await generateRegex({
        file_id: previewData.file_id,
        target_column: targetColumn,
        natural_language: naturalLanguage.trim(),
      });
      setRegexResult(response);
    } catch (error) {
      setErrorMessage(errorToMessage(error));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleApplyReplacement() {
    if (!previewData || !regexResult) {
      setReplaceError("Generate a regex before applying a replacement.");
      return;
    }

    setReplaceLoading(true);
    setReplaceError(null);
    setReplaceResult(null);

    try {
      const response = await applyReplacement({
        file_id: previewData.file_id,
        target_column: regexResult.target_column,
        regex: regexResult.regex,
        flags: regexResult.flags,
        replacement: replacementValue,
      });
      setReplaceResult(response);
    } catch (error) {
      setReplaceError(errorToMessage(error));
    } finally {
      setReplaceLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <FileUploader
        isUploading={isUploading}
        onUpload={handleUpload}
        onClientError={(message) => setErrorMessage(message || null)}
      />
      <ErrorMessage message={errorMessage} />
      <DataPreviewTable data={previewData} />
      <RegexGenerationPanel
        columns={previewData?.columns ?? []}
        hasUploadedFile={Boolean(previewData)}
        isGenerating={isGenerating}
        naturalLanguage={naturalLanguage}
        targetColumn={targetColumn}
        onGenerate={handleGenerateRegex}
        onNaturalLanguageChange={(value) => {
          setNaturalLanguage(value);
          setRegexResult(null);
          setReplaceResult(null);
          setReplaceError(null);
        }}
        onTargetColumnChange={(value) => {
          setTargetColumn(value);
          setRegexResult(null);
          setReplaceResult(null);
          setReplaceError(null);
        }}
      />
      <RegexPreviewCard result={regexResult} />
      {regexResult ? (
        <ReplacementPanel
          isLoading={replaceLoading}
          replacementValue={replacementValue}
          onApply={handleApplyReplacement}
          onReplacementChange={(value) => {
            setReplacementValue(value);
            setReplaceResult(null);
            setReplaceError(null);
          }}
        />
      ) : null}
      <ErrorMessage message={replaceError} />
      <ProcessedDataTable result={replaceResult} />
      <ReplacementStatsCard stats={replaceResult?.stats ?? null} />
    </main>
  );
}

function errorToMessage(error: unknown): string {
  if (error instanceof RegexApiError) {
    return error.message;
  }

  if (error instanceof UploadApiError) {
    return error.message;
  }

  return "The request failed. Check the backend and try again.";
}
