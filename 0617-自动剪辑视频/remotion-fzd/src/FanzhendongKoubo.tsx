import {Audio} from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {CaptionLayer} from "./caption-layer";

const title = "樊振东真正可怕的地方";

export const FanzhendongKoubo = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const seconds = frame / fps;
  const progress = frame / durationInFrames;

  const entrance = interpolate(frame, [0, 0.8 * fps], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const imageScale = interpolate(progress, [0, 1], [1.04, 1.16]);
  const portraitY = interpolate(frame, [0, 1.2 * fps], [44, 0], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pulse = 0.5 + Math.sin(seconds * Math.PI * 2) * 0.5;

  return (
    <AbsoluteFill style={{backgroundColor: "#07111f", overflow: "hidden"}}>
      <Img
        src={staticFile("fan-zhendong.jpeg")}
        style={{
          position: "absolute",
          inset: -80,
          width: 1240,
          height: 2080,
          objectFit: "cover",
          filter: "blur(28px) saturate(1.05) brightness(0.56)",
          transform: `scale(${imageScale})`,
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(3,7,18,0.32) 0%, rgba(7,17,31,0.08) 34%, rgba(4,8,15,0.92) 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: -120,
          right: -120,
          top: 0,
          height: 760,
          background:
            "linear-gradient(120deg, rgba(238,42,84,0.42), rgba(48,213,200,0.25), rgba(255,229,93,0.16))",
          opacity: 0.55 + pulse * 0.12,
          transform: `translateY(${interpolate(progress, [0, 1], [-80, 60])}px) rotate(-8deg)`,
          filter: "blur(38px)",
        }}
      />
      <Img
        src={staticFile("fan-zhendong.jpeg")}
        style={{
          position: "absolute",
          left: 70,
          top: 268 + portraitY,
          width: 940,
          height: 1180,
          objectFit: "cover",
          objectPosition: "50% 22%",
          borderRadius: 36,
          boxShadow: "0 46px 120px rgba(0,0,0,0.48)",
          border: "3px solid rgba(255,255,255,0.26)",
          transform: `scale(${0.96 + entrance * 0.04})`,
          opacity: entrance,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: 82,
          color: "white",
          opacity: entrance,
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "10px 18px",
            border: "1.5px solid rgba(255,255,255,0.36)",
            borderRadius: 999,
            fontSize: 28,
            fontWeight: 800,
            letterSpacing: 0,
            color: "#ffe55d",
            background: "rgba(3,7,18,0.36)",
          }}
        >
          10 秒口播
        </div>
        <div
          style={{
            marginTop: 28,
            fontSize: 76,
            lineHeight: 1.08,
            fontWeight: 950,
            letterSpacing: 0,
            textShadow: "0 8px 26px rgba(0,0,0,0.62)",
          }}
        >
          {title}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          bottom: 84,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          color: "rgba(255,255,255,0.72)",
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 0,
        }}
      >
        <span>图源：XIAOYU TANG / CC BY-SA 2.0</span>
        <span>乒乓球 | 高光口播</span>
      </div>
      <CaptionLayer />
      <Audio src={staticFile("fan-zhendong-voice.mp3")} volume={0.98} />
    </AbsoluteFill>
  );
};
