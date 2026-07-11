import {Composition} from "remotion";
import {FanzhendongKoubo} from "./FanzhendongKoubo";

export const RemotionRoot = () => {
  return (
    <Composition
      id="FanzhendongKoubo"
      component={FanzhendongKoubo}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
