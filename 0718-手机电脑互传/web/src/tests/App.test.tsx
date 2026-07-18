import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { App } from "../App";

it("消费二维码令牌后展示手机上传页", () => {
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/?token=session-token");

  render(<App />);

  expect(screen.getByLabelText("选择照片和视频")).toBeInTheDocument();
  expect(window.location.search).toBe("");
  expect(window.sessionStorage.getItem("phone2computer-token")).toBe("session-token");
});
