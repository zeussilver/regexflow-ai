import axios from "axios";
import { apiClient } from "./client";
import type {
  CheckRule,
  DataHolder,
  ProductCheckResult,
  ProductCheckRun,
} from "../types/productChecks";

export const listHolders = async () =>
  (await apiClient.get<{ holders: DataHolder[] }>("/product-checks/holders/"))
    .data.holders;
export const listCheckRules = async () =>
  (
    await apiClient.get<{ ruleset_version: string; rules: CheckRule[] }>(
      "/product-checks/rules/",
    )
  ).data;
export const listProductChecks = async () =>
  (await apiClient.get<{ runs: ProductCheckRun[] }>("/product-checks/")).data
    .runs;
export const getProductCheck = async (id: string) =>
  (await apiClient.get<ProductCheckResult>(`/product-checks/${id}/`)).data;
export const checkLiveHolder = async (holder: string, includeDetails: boolean) =>
  (
    await apiClient.post<ProductCheckResult>("/product-checks/", {
      holder,
      include_details: includeDetails,
    })
  ).data;
export async function checkUploadedProducts(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return (await apiClient.post<ProductCheckResult>("/product-checks/", formData))
    .data;
}
export function productCheckError(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data?.error?.message)
    return error.response.data.error.message;
  return "The product check failed. Check the backend and try again.";
}
