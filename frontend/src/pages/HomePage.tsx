import { useState } from "react";

import { uploadFile } from "../api/files";
import { applyReplacement, generateRegex } from "../api/regex";
import { normalizePhones, redactPii } from "../api/transformations";
import DataPreviewTable from "../components/DataPreviewTable";
import ErrorMessage from "../components/ErrorMessage";
import FileUploader from "../components/FileUploader";
import PhoneNormalizationPanel from "../components/PhoneNormalizationPanel";
import PiiRedactionPanel from "../components/PiiRedactionPanel";
import ProcessedDataTable from "../components/ProcessedDataTable";
import RegexGenerationPanel from "../components/RegexGenerationPanel";
import RegexPreviewCard from "../components/RegexPreviewCard";
import ReplacementPanel from "../components/ReplacementPanel";
import ReplacementStatsCard from "../components/ReplacementStatsCard";
import TransformationModeTabs from "../components/TransformationModeTabs";
import TransformationResultTable from "../components/TransformationResultTable";
import TransformationStatsCard from "../components/TransformationStatsCard";
import { FileUploadResponse, UploadApiError } from "../types/files";
import { RegexApiError, RegexGenerateResponse, RegexReplaceResponse } from "../types/regex";
import {
  PhoneNormalizationResponse,
  PhoneTargetFormat,
  PiiRedactionResponse,
  PiiReplacementStrategy,
  PiiType,
  TransformationApiError,
  TransformationMode,
} from "../types/transformations";

const defaultPiiTypes: PiiType[] = ["email", "phone", "credit_card", "url"];
const defaultPiiInstruction =
  "Redact common sensitive personal information from selected or text-like columns.";
const defaultPhoneInstruction = "Normalize phone numbers to international format";

export default function HomePage() {
  const [previewData, setPreviewData] = useState<FileUploadResponse | null>(null);
  const [regexResult, setRegexResult] = useState<RegexGenerateResponse | null>(null);
  const [replaceResult, setReplaceResult] = useState<RegexReplaceResponse | null>(null);
  const [piiResult, setPiiResult] = useState<PiiRedactionResponse | null>(null);
  const [phoneResult, setPhoneResult] = useState<PhoneNormalizationResponse | null>(null);
  const [targetColumn, setTargetColumn] = useState("");
  const [naturalLanguage, setNaturalLanguage] = useState("");
  const [replacementValue, setReplacementValue] = useState("REDACTED");
  const [transformationMode, setTransformationMode] =
    useState<TransformationMode>("pii_redaction");
  const [piiTargetColumns, setPiiTargetColumns] = useState<string[]>([]);
  const [piiTypes, setPiiTypes] = useState<PiiType[]>(defaultPiiTypes);
  const [piiReplacementStrategy, setPiiReplacementStrategy] =
    useState<PiiReplacementStrategy>("typed_placeholders");
  const [phoneTargetColumn, setPhoneTargetColumn] = useState("");
  const [phoneNaturalLanguage, setPhoneNaturalLanguage] = useState(defaultPhoneInstruction);
  const [phoneDefaultRegion, setPhoneDefaultRegion] = useState("AU");
  const [phoneTargetFormat, setPhoneTargetFormat] = useState<PhoneTargetFormat>("E164");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [replaceError, setReplaceError] = useState<string | null>(null);
  const [transformationError, setTransformationError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [replaceLoading, setReplaceLoading] = useState(false);
  const [piiLoading, setPiiLoading] = useState(false);
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const activeTransformationResult =
    transformationMode === "pii_redaction" ? piiResult : phoneResult;

  async function handleUpload(file: File) {
    setIsUploading(true);
    setErrorMessage(null);
    setReplaceError(null);
    setTransformationError(null);
    setRegexResult(null);
    setReplaceResult(null);
    setPiiResult(null);
    setPhoneResult(null);
    setTargetColumn("");
    setPiiTargetColumns([]);
    setPhoneTargetColumn("");

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

  async function handleApplyPiiRedaction() {
    if (!previewData) {
      setTransformationError("Upload a CSV or XLSX file before applying PII redaction.");
      return;
    }

    if (piiTypes.length === 0) {
      setTransformationError("Choose at least one PII type before applying redaction.");
      return;
    }

    setPiiLoading(true);
    setTransformationError(null);
    setPiiResult(null);

    try {
      const response = await redactPii({
        file_id: previewData.file_id,
        natural_language: defaultPiiInstruction,
        ...(piiTargetColumns.length > 0 ? { target_columns: piiTargetColumns } : {}),
        pii_types: piiTypes,
        replacement_strategy: piiReplacementStrategy,
      });
      setPiiResult(response);
    } catch (error) {
      setTransformationError(errorToMessage(error));
    } finally {
      setPiiLoading(false);
    }
  }

  async function handleNormalizePhones() {
    if (!previewData) {
      setTransformationError("Upload a CSV or XLSX file before normalizing phone numbers.");
      return;
    }

    if (!phoneTargetColumn) {
      setTransformationError("Choose a target column before normalizing phone numbers.");
      return;
    }

    if (!phoneNaturalLanguage.trim()) {
      setTransformationError("Enter an instruction before normalizing phone numbers.");
      return;
    }

    if (!phoneDefaultRegion.trim()) {
      setTransformationError("Enter a default region before normalizing phone numbers.");
      return;
    }

    setPhoneLoading(true);
    setTransformationError(null);
    setPhoneResult(null);

    try {
      const response = await normalizePhones({
        file_id: previewData.file_id,
        target_columns: [phoneTargetColumn],
        natural_language: phoneNaturalLanguage.trim(),
        default_region: phoneDefaultRegion.trim().toUpperCase(),
        target_format: phoneTargetFormat,
      });
      setPhoneResult(response);
    } catch (error) {
      setTransformationError(errorToMessage(error));
    } finally {
      setPhoneLoading(false);
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
      <TransformationModeTabs
        mode={transformationMode}
        onModeChange={(mode) => {
          setTransformationMode(mode);
          setTransformationError(null);
        }}
      />
      {transformationMode === "pii_redaction" ? (
        <PiiRedactionPanel
          columns={previewData?.columns ?? []}
          hasUploadedFile={Boolean(previewData)}
          isLoading={piiLoading}
          replacementStrategy={piiReplacementStrategy}
          selectedPiiTypes={piiTypes}
          selectedTargetColumns={piiTargetColumns}
          onApply={handleApplyPiiRedaction}
          onPiiTypesChange={(value) => {
            setPiiTypes(value);
            setPiiResult(null);
            setTransformationError(null);
          }}
          onReplacementStrategyChange={(value) => {
            setPiiReplacementStrategy(value);
            setPiiResult(null);
            setTransformationError(null);
          }}
          onTargetColumnsChange={(value) => {
            setPiiTargetColumns(value);
            setPiiResult(null);
            setTransformationError(null);
          }}
        />
      ) : (
        <PhoneNormalizationPanel
          columns={previewData?.columns ?? []}
          defaultRegion={phoneDefaultRegion}
          hasUploadedFile={Boolean(previewData)}
          isLoading={phoneLoading}
          naturalLanguage={phoneNaturalLanguage}
          targetColumn={phoneTargetColumn}
          targetFormat={phoneTargetFormat}
          onDefaultRegionChange={(value) => {
            setPhoneDefaultRegion(value);
            setPhoneResult(null);
            setTransformationError(null);
          }}
          onNaturalLanguageChange={(value) => {
            setPhoneNaturalLanguage(value);
            setPhoneResult(null);
            setTransformationError(null);
          }}
          onNormalize={handleNormalizePhones}
          onTargetColumnChange={(value) => {
            setPhoneTargetColumn(value);
            setPhoneResult(null);
            setTransformationError(null);
          }}
          onTargetFormatChange={(value) => {
            setPhoneTargetFormat(value);
            setPhoneResult(null);
            setTransformationError(null);
          }}
        />
      )}
      <ErrorMessage message={transformationError} />
      <TransformationResultTable result={activeTransformationResult} />
      <TransformationStatsCard result={activeTransformationResult} />
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

  if (error instanceof TransformationApiError) {
    return error.message;
  }

  return "The request failed. Check the backend and try again.";
}
