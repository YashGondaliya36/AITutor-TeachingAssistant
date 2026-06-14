import React from "react";
import cn from "classnames";
import { Lightbulb } from "lucide-react";
import { useHint } from "../../contexts/HintContext";

interface HintButtonProps {
  isGradingSidebarOpen?: boolean;
  inline?: boolean; // New prop to control inline vs fixed positioning
}

const HintButton: React.FC<HintButtonProps> = ({ isGradingSidebarOpen = false, inline = false }) => {
  const { showHints, toggleHints } = useHint();

  return (
    <button
      onClick={toggleHints}
      className={cn(
        "flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5",
        "border-[2px] md:border-[3px] border-black dark:border-white",
        showHints
          ? "bg-[#FFD93D] dark:bg-[#FFD93D] text-black"
          : "bg-[#FFFDF5] dark:bg-[#000000] text-black dark:text-white hover:text-black",
        "hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D]",
        "transition-all duration-500",
        "shadow-[1px_1px_0_0_rgba(0,0,0,1)] md:shadow-[2px_2px_0_0_rgba(0,0,0,1)]",
        "dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)] md:dark:shadow-[2px_2px_0_0_rgba(255,255,255,0.3)]",
        "hover:shadow-[2px_2px_0_0_rgba(0,0,0,1)] md:hover:shadow-[3px_3px_0_0_rgba(0,0,0,1)]",
        "hover:translate-x-0.5 hover:translate-y-0.5",
        "active:translate-x-1 active:translate-y-1 active:shadow-none",
        // Fixed positioning only when not inline
        !inline && "fixed bottom-4 z-40",
        !inline && (isGradingSidebarOpen 
          ? "left-[264px] md:left-[268px]" 
          : "left-[48px] md:left-[48px]")
      )}
      style={!inline ? {
        transition: "left 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
      } : undefined}
      title={showHints ? "Hide Hint" : "Show Hint"}
    >
      <Lightbulb className={cn(
        "w-4 h-4 md:w-5 md:h-5 font-bold",
        showHints && "fill-current"
      )} />
      <span className="text-xs md:text-sm font-black uppercase tracking-tight">
        Hint
      </span>
    </button>
  );
};

export default HintButton;
