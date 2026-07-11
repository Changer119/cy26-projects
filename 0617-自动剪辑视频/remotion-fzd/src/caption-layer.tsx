import {useCallback, useEffect, useMemo, useState} from "react";
import type {Caption} from "@remotion/captions";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";

type CaptionCardProps = {
  caption: Caption;
};

const emphasisColor = "#ffe55d";

const CaptionCard = ({caption}: CaptionCardProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enterFrames = Math.round(0.22 * fps);
  const opacity = interpolate(frame, [0, enterFrames], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, enterFrames], [38, 0], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textParts = caption.text.split(/(\*[^*]+\*)/g).filter(Boolean);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        padding: "0 84px 250px",
        opacity,
      }}
    >
      <div
        style={{
          transform: `translateY(${translateY}px)`,
          maxWidth: 900,
          borderRadius: 28,
          padding: "26px 34px",
          color: "white",
          fontSize: 64,
          fontWeight: 900,
          lineHeight: 1.16,
          letterSpacing: 0,
          textAlign: "center",
          textShadow: "0 5px 18px rgba(0,0,0,0.78)",
          background: "rgba(10, 16, 28, 0.66)",
          boxShadow: "0 18px 60px rgba(0,0,0,0.34)",
          border: "2px solid rgba(255,255,255,0.2)",
        }}
      >
        {textParts.map((token, index) => {
          const highlighted = token.startsWith("*") && token.endsWith("*");
          const text = highlighted ? token.slice(1, -1) : token;
          return (
            <span
              key={`${caption.startMs}-${index}`}
              style={{color: highlighted ? emphasisColor : "white"}}
            >
              {text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const CaptionLayer = () => {
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const {fps, durationInFrames} = useVideoConfig();
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const [handle] = useState(() => delayRender("加载口播字幕"));

  const loadCaptions = useCallback(async () => {
    try {
      const response = await fetch(staticFile("captions.json"));
      const data = (await response.json()) as Caption[];
      setCaptions(data);
      continueRender(handle);
    } catch (error) {
      cancelRender(error);
    }
  }, [cancelRender, continueRender, handle]);

  useEffect(() => {
    loadCaptions();
  }, [loadCaptions]);

  const captionSequences = useMemo(() => {
    if (!captions) {
      return [];
    }

    return captions.map((caption) => {
      const from = Math.round((caption.startMs / 1000) * fps);
      const end = Math.round((caption.endMs / 1000) * fps);
      return {
        caption,
        from,
        duration: Math.max(1, Math.min(end, durationInFrames) - from),
      };
    });
  }, [captions, durationInFrames, fps]);

  if (!captions) {
    return null;
  }

  return (
    <AbsoluteFill>
      {captionSequences.map(({caption, from, duration}) => (
        <Sequence
          key={caption.startMs}
          from={from}
          durationInFrames={duration}
        >
          <CaptionCard caption={caption} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
