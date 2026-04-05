import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:5000",
  timeout: 15000,
});

export const captureFingerprint = async (payload = {}) => {
  const response = await api.post("/capture", payload);
  return response.data;
};

export const enrollUser = async (payload) => {
  const response = await api.post("/enroll", payload);
  return response.data;
};

export const verifyFingerprint = async (payload) => {
  const response = await api.post("/verify", payload);
  return response.data;
};

export const fetchAttendance = async () => {
  const response = await api.get("/attendance");
  return response.data;
};

export const fetchUsers = async () => {
  const response = await api.get("/users");
  return response.data;
};

export const fetchHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const deleteUser = async (userId) => {
  const response = await api.delete(`/users/${userId}`);
  return response.data;
};
