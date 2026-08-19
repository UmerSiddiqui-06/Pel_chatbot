import pelLogo from "../../assets/pel-logo.png";
import clsx from "clsx";

interface Props {
  size?: number;
  animated?: boolean;
  className?: string;
}

/**
 * The signature device of this UI: a 45deg-rotated square, glassy and
 * gradient-filled, with the PEL roundel counter-rotated back to upright
 * inside it. It recurs as the splash mark, the assistant's avatar, and
 * (in outline form) the send button — one geometric idea carried through
 * the whole product rather than a different shape in every place.
 */
export function PelMark({ size = 40, animated = false, className }: Props) {
  return (
    <div
      className={clsx(
        "flex items-center justify-center rounded-lg bg-gradient-to-br from-pel-500 to-pel-800 shadow-lg shadow-pel-900/30 rotate-45",
        animated && "animate-mark-in",
        className
      )}
      style={{ width: size, height: size }}
    >
      <img
        src={pelLogo}
        alt="PEL"
        className="-rotate-45"
        style={{ width: size * 0.56, height: size * 0.56 }}
      />
    </div>
  );
}
