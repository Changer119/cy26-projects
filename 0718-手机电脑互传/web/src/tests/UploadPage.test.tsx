import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { UploadPage } from "../components/UploadPage";
import type { UploadRunner } from "../upload";

it("批量选择照片和视频后立即进入上传队列", () => {
  const started: string[] = [];
  const runner: UploadRunner = (file) => {
    started.push(file.name);
    return { abort: async () => undefined };
  };
  render(<UploadPage runner={runner} />);
  const files = [
    new File(["photo"], "IMG_001.jpg", { type: "image/jpeg" }),
    new File(["video"], "VID_001.mp4", { type: "video/mp4" }),
  ];

  fireEvent.change(screen.getByLabelText("选择照片和视频"), { target: { files } });

  expect(screen.getByText("2 个文件")).toBeInTheDocument();
  expect(screen.getByText("IMG_001.jpg")).toBeInTheDocument();
  expect(screen.getByText("VID_001.mp4")).toBeInTheDocument();
  expect(started).toEqual(["IMG_001.jpg", "VID_001.mp4"]);
});

it("提供把浏览器配对信息交给原生 App 的入口", () => {
  window.history.replaceState({}, "", "/?token=app-token");
  const runner: UploadRunner = () => ({ abort: async () => undefined });

  render(<UploadPage runner={runner} />);

  const link = screen.getByRole("link", { name: "在 App 中继续" });
  expect(link).toHaveAttribute(
    "href",
    `phone2computer://pair?server=${encodeURIComponent(window.location.origin)}&token=app-token`,
  );
  expect(screen.getByRole("link", { name: "下载华为版 APK" })).toHaveAttribute(
    "href",
    "/Phone2Computer-v2.apk",
  );
});
