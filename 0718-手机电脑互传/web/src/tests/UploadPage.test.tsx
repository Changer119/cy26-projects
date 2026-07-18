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
