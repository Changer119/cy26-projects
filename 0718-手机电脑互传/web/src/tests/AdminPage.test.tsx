import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { AdminPage } from "../components/AdminPage";

it("展示手机扫码地址和接收目录", async () => {
  render(
    <AdminPage
      loadConfig={async () => ({
        upload_url: "http://192.168.31.20:8765/?token=secret",
        output_directory: "/Users/test/Downloads/Phone2Computer",
      })}
    />,
  );

  expect(await screen.findByText("http://192.168.31.20:8765/?token=secret")).toBeInTheDocument();
  expect(screen.getByText("/Users/test/Downloads/Phone2Computer")).toBeInTheDocument();
  expect(screen.getByText("用华为手机扫码开始传输")).toBeInTheDocument();
});
