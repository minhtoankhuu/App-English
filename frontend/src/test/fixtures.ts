import type { UserOut } from "../types/auth";

export const adminUser: UserOut = {
  id: "admin-1",
  email: "admin@example.com",
  full_name: "Admin",
  role: "admin",
  is_active: true,
};

export const teacherUser: UserOut = {
  ...adminUser,
  id: "teacher-1",
  role: "teacher",
};
