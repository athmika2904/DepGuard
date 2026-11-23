
import axios from "axios";
import type { ScanResult } from "../types";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000
});

export async function uploadLockfile(file: File): Promise<ScanResult> {
  const formData = new FormData();

  formData.append("lockfile", file);

  const response = await api.post<ScanResult>(
    "/scan",
    formData
  );

  return response.data;
}

export default api;

