import { motion } from "framer-motion";

interface LogoProps {
  size?: number;
  className?: string;
}

/**
 * Yomi mark. Solid black square with the kanji 読 in serif.
 * Mirrors the editorial black-square feel of the Kodansha logo without
 * copying any of their artwork.
 */
export function YomiLogo({ size = 56, className = "" }: LogoProps) {
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.2, 0.7, 0.1, 1] }}
      className={className}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 64 64" width={size} height={size} aria-label="Yomi">
        <rect x="0" y="0" width="64" height="64" fill="#0a0a0a" />
        <text
          x="32"
          y="48"
          fontFamily='"Noto Serif JP", serif'
          fontWeight={700}
          fontSize={44}
          textAnchor="middle"
          fill="#fafaf7"
        >
          読
        </text>
      </svg>
    </motion.div>
  );
}
