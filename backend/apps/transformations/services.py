from typing import Optional

from apps.files.services import save_processed_dataframe
from apps.regex_engine import match_preview

from . import phone_normalizer, phone_rule_service, pii_policy_service, pii_redactor
from .transformation_stats import cell_to_string, is_nullish, preview_records


def run_pii_redaction(
    *,
    file_id: str,
    target_columns: list[str],
    natural_language: str,
    pii_types: Optional[list[str]],
    replacement_strategy: str,
) -> dict:
    dataframe = match_preview.load_uploaded_dataframe(file_id)
    sample_values = pii_policy_service.sample_pii_values(
        dataframe=dataframe,
        target_columns=target_columns,
    )
    llm_policy = pii_policy_service.generate_pii_redaction_policy(
        natural_language=natural_language,
        target_columns=target_columns,
        requested_pii_types=pii_types,
        requested_replacement_strategy=replacement_strategy,
        sample_values=sample_values,
    )
    policy = pii_policy_service.resolve_policy(
        llm_policy=llm_policy,
        target_columns=target_columns,
        requested_pii_types=pii_types,
        requested_replacement_strategy=replacement_strategy,
    )
    redaction_result = pii_redactor.apply_pii_redaction(
        dataframe=dataframe,
        target_columns=target_columns,
        pii_types=policy["pii_types"],
        replacement_strategy=policy["replacement_strategy"],
    )
    processed_file_id = save_processed_dataframe(redaction_result["processed_dataframe"])

    return {
        "transformation": "pii_redaction",
        "file_id": file_id,
        "processed_file_id": processed_file_id,
        "target_columns": redaction_result["target_columns"],
        "pii_types": policy["pii_types"],
        "replacement_strategy": policy["replacement_strategy"],
        "policy": policy,
        "columns": list(redaction_result["processed_dataframe"].columns),
        "row_count": int(len(redaction_result["processed_dataframe"])),
        "preview_limit": redaction_result["preview_limit"],
        "processed_preview": preview_records(redaction_result["preview_dataframe"]),
        "stats": redaction_result["stats"],
        "warnings": redaction_result["warnings"],
    }


def run_phone_normalization(
    *,
    file_id: str,
    target_columns: list[str],
    validated_data: dict,
) -> dict:
    dataframe = match_preview.load_uploaded_dataframe(file_id)
    rule = _resolve_phone_rule(
        dataframe=dataframe,
        target_columns=target_columns,
        validated_data=validated_data,
    )
    normalization_result = phone_normalizer.apply_phone_normalization(
        dataframe=dataframe,
        target_columns=target_columns,
        rule=rule,
    )
    processed_file_id = save_processed_dataframe(
        normalization_result["processed_dataframe"]
    )

    return {
        "transformation": "phone_normalization",
        "file_id": file_id,
        "processed_file_id": processed_file_id,
        "target_columns": target_columns,
        "rule": normalization_result["rule"],
        "columns": list(normalization_result["processed_dataframe"].columns),
        "row_count": int(len(normalization_result["processed_dataframe"])),
        "preview_limit": normalization_result["preview_limit"],
        "processed_preview": preview_records(
            normalization_result["preview_dataframe"]
        ),
        "stats": normalization_result["stats"],
        "warnings": normalization_result["warnings"],
    }


def _resolve_phone_rule(*, dataframe, target_columns, validated_data):
    explicit_rule = dict(validated_data.get("rule") or {})
    for field_name in ("target_format", "default_region", "preserve_invalid"):
        if field_name in validated_data:
            explicit_rule[field_name] = validated_data[field_name]

    natural_language = validated_data.get("natural_language", "")
    sample_values = _sample_phone_values(dataframe, target_columns)
    llm_rule = phone_rule_service.generate_phone_normalization_rule(
        natural_language=natural_language,
        target_columns=target_columns,
        sample_values=sample_values,
    )
    llm_rule.update(explicit_rule)
    return llm_rule


def _sample_phone_values(dataframe, target_columns: list[str]) -> list[str]:
    sample_values = []
    for column in target_columns:
        if column not in dataframe.columns:
            raise phone_normalizer.PhoneNormalizationError(
                code="COLUMN_NOT_FOUND",
                message=f"Column '{column}' was not found in the uploaded file.",
            )

        for value in dataframe[column].head(50):
            if is_nullish(value):
                continue
            string_value = cell_to_string(value).strip()
            if not string_value:
                continue
            sample_values.append(string_value)
            if len(sample_values) == phone_rule_service.SAMPLE_VALUE_LIMIT:
                return sample_values

    return sample_values
