options.tsx:
<code>
// options.tsx
import React, { useCallback, useEffect, useState } from "react"
import styled from "styled-components"
import { Storage } from "@plasmohq/storage"; // Import Storage
import { useFirebase } from "~firebase/hook"; // Import Firebase hook

import type { ThemeSettings } from "~storage/theme"
import { themeStorage } from "~storage/theme"

import "./style.css" // Import style.css normally

const Container = styled.div`
  max-width: 800px;
  margin: 2rem auto;
  padding: 0 1rem;
  /* Use CSS variables for styling */
  font-family: var(--font-family);
  background-color: var(--color-background);
  color: var(--color-text);
`

const Section = styled.section`
  margin-bottom: 2rem;
  padding: 1.5rem;
  border-radius: 0.5rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-secondary);
`

const ColorInput = styled.input`
  width: 50px;
  height: 30px;
  padding: 0;
  border: none;
  border-radius: 4px;
  cursor: pointer;

  &::-webkit-color-swatch-wrapper {
    padding: 0;
  }

  &::-webkit-color-swatch {
    border: none;
    border-radius: 4px;
  }
`

// Use plain <select> and apply Tailwind classes
const Select = ({
  value,
  onChange,
  children,
  className = ""
}: {
  value: string
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void
  children: React.ReactNode
  className?: string
}) => (
  <select
    value={value}
    onChange={onChange}
    className={`bg-background text-text p-2 rounded-md border border-secondary w-48 ${className}`} // Tailwind + custom class
  >
    {children}
  </select>
)
//removed styled components for select, input - using tailwind instead

const FontSelect = ({ value, onChange, children }) => (
  <Select value={value} onChange={onChange} className={`font-${value}`}>
    {children}
  </Select>
)

// Simple debounce function
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(() => {
      func(...args)
      timeout = null
    }, wait)
  }
}

// Reusable size adjustment buttons component
const SizeAdjustButtons = ({ onIncrease, onDecrease, label }) => (
  <div className="flex items-center gap-2">
    <button
      onClick={onDecrease}
      className="w-6 h-6 flex items-center justify-center bg-background border border-secondary rounded-md text-text hover:bg-background2 focus:outline-none focus:ring-2 focus:ring-primary"
      title={`Decrease ${label}`}
    >
      <span className="text-sm font-bold">-</span>
    </button>
    <button
      onClick={onIncrease}
      className="w-6 h-6 flex items-center justify-center bg-background border border-secondary rounded-md text-text hover:bg-background2 focus:outline-none focus:ring-2 focus:ring-primary"
      title={`Increase ${label}`}
    >
      <span className="text-sm font-bold">+</span>
    </button>
  </div>
)

function CustomGoogleFontInput({
  fontFamily,
  setFontFamily
}: {
  fontFamily: string
  setFontFamily: (font: string) => void
}) {
  const [input, setInput] = useState(fontFamily || "");
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "success">("idle");
  const [error, setError] = useState<string>("");

  // Helper to convert input to Google Fonts casing (capitalize each word)
  const normalizeFontName = (name: string) =>
    name
      .trim()
      .split(/\s+/)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");

  // Helper to create a Google Fonts link tag
  // Use the raw user input for the URL (lowercase, pluses), but normalized for CSS
  const injectGoogleFont = (rawFont: string) => {
    const fontParam = rawFont.trim().toLowerCase().replace(/\s+/g, "+");
    const href = `https://fonts.googleapis.com/css?family=${fontParam}:400,700&display=swap`;
    // Avoid duplicate links
    if (!document.querySelector(`link[data-google-font="${fontParam}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.setAttribute("data-google-font", fontParam);
      document.head.appendChild(link);
    }
  };

  // Try to load and verify the font (with width comparison)
  const verifyAndApplyFont = async (rawFont: string) => {
    setStatus("loading");
    setError("");
    const normalizedFont = normalizeFontName(rawFont);
    injectGoogleFont(rawFont);
    try {
      // Wait for font to load (try both normal and bold)
      await Promise.all([
        document.fonts.load(`400 1em "${normalizedFont}"`),
        document.fonts.load(`700 1em "${normalizedFont}"`)
      ]);
      await document.fonts.ready;

      // Check with document.fonts.check first
      if (document.fonts.check(`1em "${normalizedFont}"`)) {
        setFontFamily(normalizedFont);
        setStatus("success");
        return;
      }

      // Create a hidden span to measure width with the target font
      const testText = "abcdefghABCDEFGH1234567890";
      const span = document.createElement("span");
      span.textContent = testText;
      span.style.visibility = "hidden";
      span.style.position = "absolute";
      span.style.top = "-9999px";
      span.style.left = "-9999px";
      span.style.fontSize = "32px";
      span.style.fontFamily = `"${normalizedFont}", Arial, sans-serif`;
      document.body.appendChild(span);
      const targetWidth = span.offsetWidth;

      // Now set to fallback font only
      span.style.fontFamily = "Arial, sans-serif";
      const fallbackWidth = span.offsetWidth;

      document.body.removeChild(span);

      // If widths are close, accept as loaded (threshold 2px)
      if (Math.abs(targetWidth - fallbackWidth) > 2) {
        setFontFamily(normalizedFont);
        setStatus("success");
      } else {
        setStatus("error");
        setError("Font not found on Google Fonts.");
      }
    } catch {
      setStatus("error");
      setError("Failed to load font.");
    }
  };

  const handleBlurOrEnter = (e: React.KeyboardEvent | React.FocusEvent) => {
    if (
      (e as React.KeyboardEvent).type === "keydown" &&
      (e as React.KeyboardEvent).key !== "Enter"
    ) {
      return;
    }
    if (input.trim()) {
      verifyAndApplyFont(input.trim());
    }
  };

  return (
    <div className="flex flex-col gap-1 ml-2">
      <input
        type="text"
        className="p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
        placeholder="Type Google Font name (e.g. Roboto)"
        value={input}
        onChange={e => {
          setInput(e.target.value);
          setStatus("idle");
          setError("");
        }}
        onBlur={handleBlurOrEnter}
        onKeyDown={handleBlurOrEnter}
        style={{ minWidth: 200, fontFamily: input || "inherit" }}
      />
      {status === "loading" && (
        <span className="text-xs text-secondary">Checking font...</span>
      )}
      {status === "error" && (
        <span className="text-xs text-red-500">{error}</span>
      )}
      {status === "success" && (
        <span className="text-xs text-green-600">Font loaded!</span>
      )}
    </div>
  );
}

const hoverButtonDefault = {
  enabled: true,
  corner: "bottom-right"
}

type HoverButtonSettings = typeof hoverButtonDefault

export default function OptionsPage() {
  const [settings, setSettings] = useState<ThemeSettings | null>(null)
  const [hoverButtonSettings, setHoverButtonSettings] = useState<HoverButtonSettings>(hoverButtonDefault)
  const [localFonts] = useState([
    "Arial",
    "Helvetica",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Times New Roman",
    "Georgia",
    "Garamond",
    "Courier New",
    "Noto Sans",
    "Tagesschrift",
    "Underdog",
    "Space Grotesk",
    "Gidole",
    "M PLUS Code Latin",
    "Snowburst One",
    "Unkempt",
    "Macondo",
    "Macondo Swash Caps",
    "Faculty Glyphic",
    "Pangolin",
    "Handlee",
    "Almendra",
    "Quicksand",
    "Manrope",
    "Inter Tight",
    "Be Vietnam Pro",
    "Wix Madefor Display",
    "Jura",
    "Forum",
    "Griffy"
  ])
  const [newThemeName, setNewThemeName] = useState("");
  const { user } = useFirebase(); // Get user from Firebase hook
  const storage = new Storage(); // Instance for getting token

  // Debounced function to save settings
  const debouncedSaveSettings = useCallback(
    debounce((newSettings: ThemeSettings) => {
      themeStorage.setThemeSettings(newSettings)
    }, 500),
    []
  )

  // Debounced save for hover button settings
  const debouncedSaveHoverButton = useCallback(
    debounce((newSettings: HoverButtonSettings) => {
      const storage = new Storage()
      storage.set("hoverButtonSettings", newSettings)
    }, 300),
    []
  )

  // 1. Add this NEW effect FIRST (theme initialization)
  useEffect(() => {
    // Initialize theme when component mounts
    const initTheme = async () => {
      try {
        const initialSettings = await themeStorage.getThemeSettings()
        themeStorage.applyThemeToRoot(initialSettings)
      } catch (error) {
        console.error("Theme initialization failed:", error)
      }
    }
    initTheme()
    // Load hover button settings
    const loadHoverButton = async () => {
      const storage = new Storage()
      const val = await storage.get("hoverButtonSettings")
      if (val && typeof val === "object" && !Array.isArray(val)) {
        setHoverButtonSettings({ ...hoverButtonDefault, ...val })
      } else {
        setHoverButtonSettings(hoverButtonDefault)
      }
    }
    loadHoverButton()
  }, []) // <-- Empty dependency array = runs once on mount

  useEffect(() => {
    // Load saved settings and watch for changes
    const initSettings = async () => {
      const savedSettings = await themeStorage.getThemeSettings()
      setSettings(savedSettings)
    }

    initSettings()

    // Watch for external theme changes
    themeStorage.watchTheme((newSettings) => {
      setSettings(newSettings)
    })

    // Watch for hover button changes
    const storage = new Storage()
    storage.watch({
      hoverButtonSettings: (change) => {
        if (change.newValue && typeof change.newValue === "object" && !Array.isArray(change.newValue)) {
          setHoverButtonSettings({ ...hoverButtonDefault, ...change.newValue })
        } else {
          setHoverButtonSettings(hoverButtonDefault)
        }
      }
    })
  }, [])

  useEffect(() => {
    // Apply settings whenever they change locally
    if (settings) {
      // Only update storage with debounce
      debouncedSaveSettings(settings)
      // Apply visual changes immediately
      themeStorage.applyThemeToRoot(settings)
    }
  }, [settings, debouncedSaveSettings])

  useEffect(() => {
    debouncedSaveHoverButton(hoverButtonSettings)
  }, [hoverButtonSettings, debouncedSaveHoverButton])

  const handleThemeChange = (theme: "light" | "dark" | "custom") => {
    if (theme === "light" || theme === "dark") {
      const predefinedThemes = themeStorage.getThemes()
      setSettings(predefinedThemes[theme])
    } else if (settings) {
      setSettings({ ...settings, theme })
    }
  }

  const updateColors = (key: string, value: string) => {
    if (!settings) return

    if (key.startsWith("heading")) {
      const headingKey = key.split(".")[1] as "h1" | "h2" | "h3"
      setSettings({
        ...settings,
        colors: {
          ...settings.colors,
          headings: {
            ...settings.colors.headings,
            [headingKey]: value
          }
        }
      })
    } else {
      setSettings({
        ...settings,
        colors: {
          ...settings.colors,
          [key]: value
        }
      })
    }
  }

  const updateFontSize = (key: string, value: string) => {
    if (!settings) return

    setSettings({
      ...settings,
      fontSize: {
        ...settings.fontSize,
        [key]: value
      }
    })
  }

  // Helper to scale a value with unit (px, em, rem)
  const scaleValue = (value: string, factor: number) => {
    const match = value.match(/^([\d.]+)([a-z%]*)$/)
    if (!match) return value
    
    const [, numStr, unit] = match
    const num = parseFloat(numStr)
    const newValue = (num * factor).toFixed(2)
    
    // Remove trailing zeros and decimal point if needed
    const cleanValue = newValue.replace(/\.?0+$/, '')
    return `${cleanValue}${unit}`
  }

  // Function to scale all font sizes and spacing by a factor
  const scaleTextAndSpacing = (scaleFactor: number) => {
    if (!settings) return

    // Scale font sizes
    const newFontSizes = {
      body: scaleValue(settings.fontSize.body, scaleFactor),
      h1: scaleValue(settings.fontSize.h1, scaleFactor),
      h2: scaleValue(settings.fontSize.h2, scaleFactor),
      h3: scaleValue(settings.fontSize.h3, scaleFactor)
    }

    // Scale spacing
    const newSpacing = {
      lineHeight: settings.spacing.lineHeight.includes('.')
        ? (parseFloat(settings.spacing.lineHeight) * scaleFactor).toFixed(2)
        : (parseInt(settings.spacing.lineHeight) * scaleFactor).toFixed(2),
      paragraphSpacing: scaleValue(settings.spacing.paragraphSpacing, scaleFactor),
      listSpacing: scaleValue(settings.spacing.listSpacing, scaleFactor),
      listIndent: scaleValue(settings.spacing.listIndent, scaleFactor)
    }

    // Update settings with new values
    setSettings({
      ...settings,
      fontSize: newFontSizes,
      spacing: newSpacing
    })
  }

  // Increase text size and spacing by 10%
  const increaseTextSize = () => {
    scaleTextAndSpacing(1.1)
  }

  // Decrease text size and spacing by 10%
  const decreaseTextSize = () => {
    scaleTextAndSpacing(0.9)
  }

  // Individual property scaling functions
  const scaleFontSize = (key: keyof ThemeSettings["fontSize"], factor: number) => {
    if (!settings) return
    const newValue = scaleValue(settings.fontSize[key], factor)
    updateFontSize(key, newValue)
  }

  const scaleSpacing = (key: keyof ThemeSettings["spacing"], factor: number) => {
    if (!settings) return
    let newValue
    if (key === 'lineHeight') {
      const value = parseFloat(settings.spacing[key])
      newValue = (value * factor).toFixed(2)
    } else {
      newValue = scaleValue(settings.spacing[key], factor)
    }
    updateSpacing(key, newValue)
  }

  const updateSpacing = (key: string, value: string) => {
    if (!settings) return
    setSettings({
      ...settings,
      spacing: {
        ...settings.spacing,
        [key]: value
      }
    })
  }

  const handleSaveTheme = async () => {
    if (!settings || !newThemeName.trim()) {
      alert("Please enter a name for your custom theme.");
      return;
    }
    if (!user) {
      alert("You must be logged in to save themes.");
      // Optionally, trigger login flow here
      return;
    }

    try {
      const idToken = await storage.get(`auth:${user.uid}`);
      if (!idToken) {
        alert("Authentication token not found. Please log in again.");
        // Optionally, trigger login flow or token refresh
        return;
      }

      console.log("Sending theme save request:", { themeName: newThemeName, settings });

      // TODO: Replace with actual backend API URL
      const apiUrl = process.env.PLASMO_PUBLIC_API_URL || "http://localhost:8080"; 
      
      const response = await fetch(`${apiUrl}/api/themes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`
        },
        body: JSON.stringify({
          name: newThemeName,
          settings: settings // Send the entire settings object
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log("Theme saved successfully:", result);
      alert(`Theme '${newThemeName}' saved successfully!`);
      setNewThemeName(""); // Clear input field
      // Optionally, update the theme dropdown or list if needed

    } catch (error) {
      console.error("Error saving theme:", error);
      alert(`Failed to save theme: ${error.message}`);
    }
  };


  if (!settings) return <div>Loading...</div>

  // Handler to copy theme settings as JSON
  const handleCopyThemeJson = () => {
    if (!settings) return;
    const json = JSON.stringify(settings, null, 2);
    navigator.clipboard.writeText(json).then(() => {
      alert("Theme JSON copied to clipboard!");
    }, () => {
      alert("Failed to copy theme JSON.");
    });
  };

  return (
    <Container>
      <Section>
        <h2 className="text-xl font-semibold mb-4 text-secondary">Hover Button</h2>
        <div className="flex items-center gap-4 mb-4">
          <label className="text-text font-medium" htmlFor="hover-btn-enable">
            Enable Hover Button:
          </label>
          <input
            id="hover-btn-enable"
            type="checkbox"
            checked={hoverButtonSettings.enabled}
            onChange={e =>
              setHoverButtonSettings(hs => ({ ...hs, enabled: e.target.checked }))
            }
            className="w-5 h-5 accent-primary"
          />
        </div>
        <div className="flex items-center gap-4 mb-2">
          <label className="text-text font-medium" htmlFor="hover-btn-corner">
            Button Corner:
          </label>
          <select
            id="hover-btn-corner"
            value={hoverButtonSettings.corner}
            onChange={e =>
              setHoverButtonSettings(hs => ({
                ...hs,
                corner: e.target.value as HoverButtonSettings["corner"]
              }))
            }
            className="bg-background text-text p-2 rounded-md border border-secondary w-48"
            disabled={!hoverButtonSettings.enabled}
          >
            <option value="top-left">Top Left</option>
            <option value="top-right">Top Right</option>
            <option value="bottom-left">Bottom Left</option>
            <option value="bottom-right">Bottom Right</option>
          </select>
        </div>
      </Section>
      <div className="flex justify-end mb-4">
        <button
          onClick={handleCopyThemeJson}
          className="px-4 py-2 rounded-md bg-secondary text-button-text hover:bg-button-hover whitespace-nowrap"
          title="Copy current theme as JSON"
        >
          Copy Theme as JSON
        </button>
      </div>
      <h1 className="text-3xl font-bold mb-6 text-primary">Theme Settings</h1>

      <Section>
        <h2 className="text-xl font-semibold mb-4 text-secondary">
          Theme Mode
        </h2>
        <div className="mb-4">
          <Select
            value={settings.theme}
            onChange={(e) => {
              const selectedTheme = e.target.value as ThemeSettings["theme"]
              const themes = themeStorage.getThemes()
              if (selectedTheme in themes) {
                setSettings(themes[selectedTheme])
              } else {
                setSettings({ ...settings, theme: selectedTheme })
              }
            }}
            className="w-full max-w-xs">
            {Object.keys(themeStorage.getThemes()).map((theme) => (
              <option key={theme} value={theme}>
                {theme.charAt(0).toUpperCase() + theme.slice(1)}
              </option>
            ))}
            <option value="custom">Custom</option>
          </Select>
        </div>
      </Section>

      <Section>
        <h2 className="text-xl font-semibold mb-4 text-secondary">
          Typography
        </h2>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <label className="text-text">Font Family:</label>
            <Select
              value={
                localFonts.includes(settings.fontFamily)
                  ? settings.fontFamily
                  : "custom-google-font"
              }
              onChange={(e) => {
                if (e.target.value === "custom-google-font") {
                  setSettings({ ...settings, fontFamily: "" })
                } else {
                  setSettings({ ...settings, fontFamily: e.target.value })
                }
              }}
            >
              {localFonts.map((font) => (
                <option
                  key={font}
                  value={font}
                  style={{ fontFamily: font }}
                  className="font-sans"
                >
                  {font}
                </option>
              ))}
              <option value="custom-google-font">Custom Google Font...</option>
            </Select>
            {(!localFonts.includes(settings.fontFamily)) && (
              <CustomGoogleFontInput
                fontFamily={settings.fontFamily}
                setFontFamily={(font) => setSettings({ ...settings, fontFamily: font })}
              />
            )}
          </div>

          {/* Font Weight Control */}
          <div className="flex items-center gap-4 mt-4">
            <label className="text-text">Font Weight:</label>
            <Select
              value={settings.fontWeight.toString()}
              onChange={(e) => setSettings({ ...settings, fontWeight: parseInt(e.target.value) })}
            >
              <option value="100">Thin (100)</option>
              <option value="200">Extra Light (200)</option>
              <option value="300">Light (300)</option>
              <option value="400">Regular (400)</option>
              <option value="500">Medium (500)</option>
              <option value="600">Semi Bold (600)</option>
              <option value="700">Bold (700)</option>
              <option value="800">Extra Bold (800)</option>
              <option value="900">Black (900)</option>
            </Select>
          </div>
        </div>

        {/* Text Size Adjustment Buttons */}
        <div className="flex items-center gap-4 mt-4 mb-4">
          <label className="text-text font-medium">Text Size Adjustment:</label>
          <div className="flex items-center gap-2">
            <button
              onClick={decreaseTextSize}
              className="w-10 h-10 flex items-center justify-center bg-background border border-secondary rounded-md text-text hover:bg-background2 focus:outline-none focus:ring-2 focus:ring-primary"
              title="Decrease text size"
            >
              <span className="text-xl font-bold">-</span>
            </button>
            <button
              onClick={increaseTextSize}
              className="w-10 h-10 flex items-center justify-center bg-background border border-secondary rounded-md text-text hover:bg-background2 focus:outline-none focus:ring-2 focus:ring-primary"
              title="Increase text size"
            >
              <span className="text-xl font-bold">+</span>
            </button>
            <span className="text-sm text-secondary ml-2">
              Adjust all text sizes and spacing at once
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-text block mb-2">Font Sizes:</label>
            <div className="flex items-center gap-2">
              <label className="text-text min-w-[80px]">Body:</label>
              <input
                type="text"
                value={settings.fontSize.body}
                onChange={(e) => updateFontSize("body", e.target.value)}
                className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
                placeholder="e.g. 16px"
              />
              <SizeAdjustButtons
                onDecrease={() => scaleFontSize("body", 0.9)}
                onIncrease={() => scaleFontSize("body", 1.1)}
                label="body size"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-text min-w-[80px]">H1 Size:</label>
              <input
                type="text"
                value={settings.fontSize.h1}
                onChange={(e) => updateFontSize("h1", e.target.value)}
                className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
              />
              <SizeAdjustButtons
                onDecrease={() => scaleFontSize("h1", 0.9)}
                onIncrease={() => scaleFontSize("h1", 1.1)}
                label="h1 size"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-text min-w-[80px]">H2 Size:</label>
              <input
                type="text"
                value={settings.fontSize.h2}
                onChange={(e) => updateFontSize("h2", e.target.value)}
                className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
              />
              <SizeAdjustButtons
                onDecrease={() => scaleFontSize("h2", 0.9)}
                onIncrease={() => scaleFontSize("h2", 1.1)}
                label="h2 size"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-text min-w-[80px]">H3 Size:</label>
              <input
                type="text"
                value={settings.fontSize.h3}
                onChange={(e) => updateFontSize("h3", e.target.value)}
                className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
              />
              <SizeAdjustButtons
                onDecrease={() => scaleFontSize("h3", 0.9)}
                onIncrease={() => scaleFontSize("h3", 1.1)}
                label="h3 size"
              />
            </div>
            <div className="space-y-2">
              <label className="text-text block mb-2">Spacing:</label>
              <div className="flex items-center gap-2">
                <label className="text-text min-w-[120px]">Line Height:</label>
                <input
                  type="text"
                  value={settings.spacing.lineHeight}
                  onChange={(e) => updateSpacing("lineHeight", e.target.value)}
                  className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
                  placeholder="e.g. 1.5"
                />
                <SizeAdjustButtons
                  onDecrease={() => scaleSpacing("lineHeight", 0.9)}
                  onIncrease={() => scaleSpacing("lineHeight", 1.1)}
                  label="line height"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-text min-w-[120px]">
                  Paragraph Spacing:
                </label>
                <input
                  type="text"
                  value={settings.spacing.paragraphSpacing}
                  onChange={(e) =>
                    updateSpacing("paragraphSpacing", e.target.value)
                  }
                  className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
                  placeholder="e.g. 1rem"
                />
                <SizeAdjustButtons
                  onDecrease={() => scaleSpacing("paragraphSpacing", 0.9)}
                  onIncrease={() => scaleSpacing("paragraphSpacing", 1.1)}
                  label="paragraph spacing"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-text min-w-[120px]">List Spacing:</label>
                <input
                  type="text"
                  value={settings.spacing.listSpacing}
                  onChange={(e) => updateSpacing("listSpacing", e.target.value)}
                  className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
                  placeholder="e.g. 0.5rem"
                />
                <SizeAdjustButtons
                  onDecrease={() => scaleSpacing("listSpacing", 0.9)}
                  onIncrease={() => scaleSpacing("listSpacing", 1.1)}
                  label="list spacing"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-text min-w-[120px]">List Indent:</label>
                <input
                  type="text"
                  value={settings.spacing.listIndent}
                  onChange={(e) => updateSpacing("listIndent", e.target.value)}
                  className="w-24 p-2 rounded-md border border-secondary bg-background text-text focus:ring-2 focus:ring-primary"
                  placeholder="e.g. 2rem"
                />
                <SizeAdjustButtons
                  onDecrease={() => scaleSpacing("listIndent", 0.9)}
                  onIncrease={() => scaleSpacing("listIndent", 1.1)}
                  label="list indent"
                />
              </div>
            </div>
          </div>
        </div>
      </Section>

      <Section>
        <h2 className="text-xl font-semibold mb-4 text-secondary">Colors</h2>

        {/* Background Colors */}
        <h3 className="text-lg font-medium mb-3 text-secondary">
          Background Colors
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <div className="flex flex-col gap-2">
            <label className="text-text">Main Background</label>
            <div className="flex items-center gap-2">
              <ColorInput
                type="color"
                value={settings.colors.background}
                onChange={(e) => updateColors("background", e.target.value)}
                className="w-12 h-12 rounded-lg border-2 border-secondary/30"
              />
              <span className="text-sm text-secondary">
                {settings.colors.background}
              </span>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-text">Content Background</label>
            <div className="flex items-center gap-2">
              <ColorInput
                type="color"
                value={settings.colors.background2}
                onChange={(e) => updateColors("background2", e.target.value)}
                className="w-12 h-12 rounded-lg border-2 border-secondary/30"
              />
              <span className="text-sm text-secondary">
                {settings.colors.background2}
              </span>
            </div>
          </div>
        </div>

        {/* Text & Accent Colors */}
        <h3 className="text-lg font-medium mb-3 text-secondary">
          Text & Accent Colors
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="text-text">Text:</label>
            <ColorInput
              type="color"
              value={settings.colors.text}
              onChange={(e) => updateColors("text", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Primary:</label>
            <ColorInput
              type="color"
              value={settings.colors.primary}
              onChange={(e) => updateColors("primary", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Secondary:</label>
            <ColorInput
              type="color"
              value={settings.colors.secondary}
              onChange={(e) => updateColors("secondary", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Emphasis (em):</label>
            <ColorInput
              type="color"
              value={settings.colors.emphasis}
              onChange={(e) => updateColors("emphasis", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Emphasis Gradient (em):</label>
            <div className="flex items-center gap-2">
              <ColorInput
                type="color"
                value={settings.colors.emphasisGradient.color1}
                onChange={(e) => {
                  const newGradient = {
                    ...settings.colors.emphasisGradient,
                    color1: e.target.value
                  }
                  setSettings({
                    ...settings,
                    colors: { ...settings.colors, emphasisGradient: newGradient }
                  })
                }}
              />
              <ColorInput
                type="color"
                value={settings.colors.emphasisGradient.color2}
                onChange={(e) => {
                  const newGradient = {
                    ...settings.colors.emphasisGradient,
                    color2: e.target.value
                  }
                  setSettings({
                    ...settings,
                    colors: { ...settings.colors, emphasisGradient: newGradient }
                  })
                }}
              />
              <ColorInput
                type="color"
                value={settings.colors.emphasisGradient.color3}
                onChange={(e) => {
                  const newGradient = {
                    ...settings.colors.emphasisGradient,
                    color3: e.target.value
                  }
                  setSettings({
                    ...settings,
                    colors: { ...settings.colors, emphasisGradient: newGradient }
                  })
                }}
              />
            </div>
          </div>
          <div>
            <label className="text-text">Bold (strong):</label>
            <ColorInput
              type="color"
              value={settings.colors.bold}
              onChange={(e) => updateColors("bold", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Citation:</label>
            <ColorInput
              type="color"
              value={settings.colors.citation}
              onChange={(e) => updateColors("citation", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">Lite Humor:</label>
            <ColorInput
              type="color"
              value={settings.colors.liteHumor}
              onChange={(e) => updateColors("liteHumor", e.target.value)}
            />
          </div>
        </div>

        {/* Button Colors */}
        <h3 className="text-lg font-medium mb-3 text-secondary">
          Button Colors
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="text-text">Primary Button:</label>
            <ColorInput
              type="color"
              value={settings.colors.button.primary}
              onChange={(e) => {
                const newButton = { ...settings.colors.button, primary: e.target.value }
                setSettings({
                  ...settings,
                  colors: { ...settings.colors, button: newButton }
                })
              }}
            />
          </div>
          <div>
            <label className="text-text">Secondary Button:</label>
            <ColorInput
              type="color"
              value={settings.colors.button.secondary}
              onChange={(e) => {
                const newButton = { ...settings.colors.button, secondary: e.target.value }
                setSettings({
                  ...settings,
                  colors: { ...settings.colors, button: newButton }
                })
              }}
            />
          </div>
          <div>
            <label className="text-text">Button Text:</label>
            <ColorInput
              type="color"
              value={settings.colors.button.text}
              onChange={(e) => {
                const newButton = { ...settings.colors.button, text: e.target.value }
                setSettings({
                  ...settings,
                  colors: { ...settings.colors, button: newButton }
                })
              }}
            />
          </div>
          <div>
            <label className="text-text">Button Hover:</label>
            <ColorInput
              type="color"
              value={settings.colors.buttonHover}
              onChange={(e) => updateColors("buttonHover", e.target.value)}
            />
          </div>
        </div>

        {/* Heading Colors */}
        <h3 className="text-lg font-medium mb-3 text-secondary">
          Heading Colors
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="text-text">H1 Color:</label>
            <ColorInput
              type="color"
              value={settings.colors.headings.h1}
              onChange={(e) => updateColors("heading.h1", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">H2 Color:</label>
            <ColorInput
              type="color"
              value={settings.colors.headings.h2}
              onChange={(e) => updateColors("heading.h2", e.target.value)}
            />
          </div>
          <div>
            <label className="text-text">H3 Color:</label>
            <ColorInput
              type="color"
              value={settings.colors.headings.h3}
              onChange={(e) => updateColors("heading.h3", e.target.value)}
            />
          </div>
        </div>

        {/* Border Color */}
        <h3 className="text-lg font-medium mb-3 text-secondary">
          Border Color
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="text-text">Border:</label>
            <ColorInput
              type="color"
              value={settings.colors.border}
              onChange={(e) => updateColors("border", e.target.value)}
            />
          </div>
        </div>
      </Section>

    </Container>
  )
}

</code>

style.css:
<code>
/* style.css */
/* Google Fonts Imports */
/*@import url("https://fonts.googleapis.com/css2?family=Winky+Sans:wght@100..900&display=swap"); */
@import url("https://fonts.googleapis.com/css2?family=Underdog&display=swap");
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap");
@import url("https://fonts.googleapis.com/css2?family=M+PLUS+Code+Latin:wght@100..700&display=swap");
@import url("https://fonts.googleapis.com/css2?family=Gidole&family=M+PLUS+Code+Latin:wght@100..700&display=swap");

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Default theme variables - will be overridden by JS */
  --font-family: "Noto Sans", sans-serif;
  --font-weight: 400;
  --font-size-body: 15px;
  --font-size-h1: 1.8em;
  --font-size-h2: 1.5em;
  --font-size-h3: 1.3em;

  --color-background: #121212;
  --color-background2: #1e2130;
  --color-text: #e0e0e0;
  --color-primary: #f90000;
  --color-secondary: #03dac6;
  --color-border: #444444;
  --color-button-hover: #a9f9c7;
  --color-button-primary: #ff5252;
  --color-button-secondary: #4a90e2;
  --color-button-text: #ffffff;
  --color-heading-h1: #bb86fc; /* Renamed from --color-h1 */
  --color-heading-h2: #03dac6; /* Renamed from --color-h2 */
  --color-heading-h3: #8bc34a; /* Renamed from --color-h3 */
  --color-emphasis: #cf9fff; /* Added default */
  --color-emphasis-gradient-1: #cf9fff; /* Added default */
  --color-emphasis-gradient-2: #ffffff; /* Added default */
  --color-emphasis-gradient-3: #cf9fff; /* Added default */
  --emphasis-gradient: linear-gradient(
    to right,
    var(--color-emphasis-gradient-1),
    var(--color-emphasis-gradient-2),
    var(--color-emphasis-gradient-3)
  ); /* Added default */
  --color-bold: #ff5511; /* Added default */

  /* Spacing variables */
  --spacing-line-height: 1.5;
  --spacing-paragraph: 1rem;
  --spacing-list-item: 0.5rem;
  --spacing-list-indent: 1rem;
}

@layer base {
  body {
    font-family: var(--font-family);
    font-weight: var(--font-weight);
    background-color: var(--color-background);
    color: var(--color-text);
    line-height: 1.4; /* Keep this for overall line height */
    font-size: var(--font-size-body);
  }

  hr {
    margin-top: 10px;
    margin-bottom: 10px;
  }

  /* Re-introduce more specific styles, BUT use CSS variables */
  h1 {
    font-size: var(--font-size-h1);
    color: var(--color-heading-h1);
    font-weight: var(--font-weight);
    margin-top: 1.5em;
    margin-bottom: 0.8em;
  }
  h2 {
    font-size: var(--font-size-h2);
    color: var(--color-heading-h2);
    font-weight: var(--font-weight);
    margin-top: 1.2em;
    margin-bottom: 0.6em;
  }
  h3 {
    font-size: var(--font-size-h3);
    color: var(--color-heading-h3);
    font-weight: var(--font-weight);
    margin-top: 1em;
    margin-bottom: 0.5em;
  }

  strong {
    color: var(--color-bold);
    font-weight: var(--font-weight);
  }

  em {
    font-style: italic; /* Keep italic style */
    color: transparent; /* Make text transparent */
    background-clip: text; /* Clip background to text */
    -webkit-background-clip: text; /* Vendor prefix for Safari/Chrome */
    background-image: var(--emphasis-gradient); /* Apply the gradient */
  }

  /*  Override Prose styles more directly */
  .prose {
    /* Target elements WITHIN the .prose container */
    line-height: var(--spacing-line-height); /* Apply line-height */
  }

  .prose hr {
    margin-top: 10px !important;
    margin-bottom: 10px !important;
  }

  .prose p {
    margin-bottom: var(--spacing-paragraph); /* Paragraph spacing */
  }

  .prose ul,
  .prose ol {
    margin-left: var(--spacing-list-indent); /* List indentation */
    margin-bottom: var(--spacing-paragraph);
  }

  .prose ul > li,
  .prose ol > li {
    margin-bottom: var(--spacing-list-item); /* Spacing BETWEEN list items */
    padding-left: 0.1em;
  }

  .prose ul > li::marker {
    margin-right: 0.3em;
    color: var(--color-secondary);
  }

  .prose ol > li::marker {
    margin-right: 0.3em;
    color: var(--color-secondary);
  }

  /* Removed commented out strong style */
}

@layer components {
  .bg-background {
    background-color: var(--color-background);
  }
  .bg-background2 {
    background-color: var(--color-background2);
  }
  .text-text {
    color: var(--color-text);
  }
  .text-primary {
    color: var(--color-primary);
  }
  .text-secondary {
    color: var(--color-secondary);
  }
  .border-secondary {
    border-color: var(--color-secondary);
  }
  .btn-primary {
    background-color: var(--color-button-primary);
    color: var(--color-button-text);
  }
  .btn-secondary {
    background-color: var(--color-button-secondary);
    color: var(--color-button-text);
  }

  /* Additional prose styling to ensure theme colors are applied */
  .prose {
    color: var(--color-text) !important;
    max-width: none;
  }

  .prose h1 {
    color: var(--color-heading-h1) !important; /* Corrected variable */
    font-size: var(--font-size-h1) !important;
  }
  .prose h2 {
    color: var(--color-heading-h2) !important; /* Corrected variable */
    font-size: var(--font-size-h2) !important;
  }
  .prose h3 {
    color: var(--color-heading-h3) !important; /* Corrected variable */
    font-size: var(--font-size-h3) !important;
  }

  .prose strong {
    color: var(--color-bold) !important;
    font-weight: calc(var(--font-weight) + 300) !important;
  }

  .prose a {
    color: var(--color-secondary) !important;
    text-decoration: underline;
  }
  /* Removed prose ul/ol marker as its in base now */
  .prose code {
    color: var(--color-primary) !important;
    background-color: rgba(0, 0, 0, 0.1);
    padding: 0.2em 0.4em;
    border-radius: 0.25em;
  }

  .prose pre {
    background-color: var(--color-background) !important;
    border: 1px solid var(--color-border);
  }

  .prose pre code {
    background-color: transparent;
    color: var(--color-text) !important;
  }

  .prose blockquote {
    border-left-color: var(--color-secondary) !important;
    color: var(--color-text) !important;
    opacity: 0.9;
  }

  .prose table {
    border-color: var(--color-border) !important;
  }

  .prose th {
    background-color: var(--color-background2) !important;
    color: var(--color-text) !important;
  }

  .prose td {
    border-color: var(--color-border) !important;
  }

  /* Apply citation color, overriding inline yellow */
  .prose span[style*="color:yellow"],
  .prose span[style*="color: yellow"] {
    color: var(--color-citation) !important;
  }

  /* Apply lite humor color, overriding inline pink */
  .prose span[style*="color:pink"],
  .prose span[style*="color: pink"] {
    color: var(--color-lite-humor) !important;
  }
}

/* Thinking Indicator Animation */
.thinking-indicator-large {
  font-weight: bold;
  font-size: 1.8em;
  white-space: nowrap;
  perspective: 1000px;
  display: inline-block;
}

.thinking-letter,
.thinking-dot {
  display: inline-block;
  animation:
    rainbowWave 2s infinite ease-in-out,
    waveFloat 3s infinite ease-in-out,
    stretchPulse 4s infinite ease-in-out;
  transform-origin: center;
  margin: 0 0.02em;
  opacity: 0.9;
}

/* Stagger the animation delays */
.thinking-letter:nth-child(1) {
  animation-delay: 0s, 0s, 0s;
}
.thinking-letter:nth-child(2) {
  animation-delay: 0.1s, 0.2s, 0.15s;
}
.thinking-letter:nth-child(3) {
  animation-delay: 0.2s, 0.4s, 0.3s;
}
.thinking-letter:nth-child(4) {
  animation-delay: 0.3s, 0.6s, 0.45s;
}
.thinking-letter:nth-child(5) {
  animation-delay: 0.4s, 0.8s, 0.6s;
}
.thinking-letter:nth-child(6) {
  animation-delay: 0.5s, 1s, 0.75s;
}
.thinking-letter:nth-child(7) {
  animation-delay: 0.6s, 1.2s, 0.9s;
}
.thinking-letter:nth-child(8) {
  animation-delay: 0.7s, 1.4s, 1.05s;
}

.thinking-dot:nth-of-type(1) {
  animation-delay: 0.8s, 1.6s, 1.2s;
}
.thinking-dot:nth-of-type(2) {
  animation-delay: 0.9s, 1.8s, 1.35s;
}
.thinking-dot:nth-of-type(3) {
  animation-delay: 1s, 2s, 1.5s;
}
.thinking-dot:nth-of-type(4) {
  animation-delay: 1.1s, 2.2s, 1.65s;
}
.thinking-dot:nth-of-type(5) {
  animation-delay: 1.2s, 2.4s, 1.8s;
}
.thinking-dot:nth-of-type(6) {
  animation-delay: 1.3s, 2.6s, 1.95s;
}
.thinking-dot:nth-of-type(7) {
  animation-delay: 1.4s, 2.8s, 2.1s;
}
.thinking-dot:nth-of-type(8) {
  animation-delay: 1.5s, 3s, 2.25s;
}

@keyframes rainbowWave {
  0% {
    color: #ff1a1a;
  }
  15% {
    color: #ff8c1a;
  }
  30% {
    color: #ffff1a;
  }
  45% {
    color: #1aff1a;
  }
  60% {
    color: #1affff;
  }
  75% {
    color: #1a1aff;
  }
  90% {
    color: #ff1aff;
  }
  100% {
    color: #ff1a1a;
  }
}

@keyframes waveFloat {
  0%,
  100% {
    transform: translateY(0) rotateX(0deg);
  }
  25% {
    transform: translateY(-8px) rotateX(15deg);
  }
  50% {
    transform: translateY(0) rotateX(0deg);
  }
  75% {
    transform: translateY(8px) rotateX(-15deg);
  }
}

@keyframes stretchPulse {
  0%,
  100% {
    transform: scaleX(1) scaleY(1);
  }
  25% {
    transform: scaleX(1.5) scaleY(0.8);
  }
  50% {
    transform: scaleX(1) scaleY(1);
  }
  75% {
    transform: scaleX(0.8) scaleY(1.2);
  }
}

</code>

tailwind.config.js:
<code>
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: "jit",
  darkMode: "class",
  content: ["./**/*.tsx"],
  theme: {
    container: {
      center: true,
      padding: '3rem',
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px', 
        xl: '1280px',
        '2xl': '1536px', // Adjusted values for smoother transition
      },
    },
    extend: {
      typography: {
        DEFAULT: {
          css: {
            color: "var(--color-text)",
            fontSize: "var(--font-size-body)",
            h1: {
              color: "var(--color-h1)",
              fontSize: "var(--font-size-h1)"
            },
            h2: {
              color: "var(--color-h2)",
              fontSize: "var(--font-size-h2)"
            },
            h3: {
              color: "var(--color-h3)",
              fontSize: "var(--font-size-h3)"
            },
            strong: {
              color: "var(--color-bold)",
              fontWeight: "600 !important"
            },
            a: {
              color: "var(--color-secondary)"
            },
            code: {
              color: "var(--color-primary)"
            },
            "--tw-prose-bullets": "var(--color-secondary)"

            // REMOVED spacing configurations here. We're handling it in style.css
          }
        }
      }
    }
  },
  plugins: [require("@tailwindcss/typography")]
}

</code>

background\theme.ts:
<code>
import { themeStorage } from "~storage/theme"

// Initialize theme when extension starts
const init = async () => {
  // Get theme settings, which will now default to dark theme if none exists
  const settings = await themeStorage.getThemeSettings()

  // Ensure the theme is applied by explicitly setting it
  await themeStorage.setThemeSettings(settings)

  console.log("Theme initialized:", settings.theme)

  // Watch for theme changes
  themeStorage.watchTheme((settings) => {
    // Apply to content scripts if needed
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach((tab) => {
        if (tab.id) {
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: (themeSettings) => {
              const root = document.documentElement
              const { colors, fontFamily, fontSize } = themeSettings

              root.style.setProperty("--font-family", fontFamily)
              root.style.setProperty("--font-size-body", fontSize.body)
              root.style.setProperty("--font-size-h1", fontSize.h1)
              root.style.setProperty("--font-size-h2", fontSize.h2)
              root.style.setProperty("--font-size-h3", fontSize.h3)

              root.style.setProperty("--color-background", colors.background)
              root.style.setProperty("--color-background2", colors.background2)
              root.style.setProperty("--color-text", colors.text)
              root.style.setProperty("--color-primary", colors.primary)
              root.style.setProperty("--color-secondary", colors.secondary)
              root.style.setProperty("--color-border", colors.border)
              root.style.setProperty("--color-button-hover", colors.buttonHover)
              root.style.setProperty(
                "--color-button-primary",
                colors.button.primary
              )
              root.style.setProperty(
                "--color-button-secondary",
                colors.button.secondary
              )
              root.style.setProperty("--color-button-text", colors.button.text)
              root.style.setProperty("--color-h1", colors.headings.h1)
              root.style.setProperty("--color-h2", colors.headings.h2)
              root.style.setProperty("--color-h3", colors.headings.h3)
            },
            args: [settings]
          })
        }
      })
    })
  })
}

init()

</code>

components\AnalysisView.tsx:
<code>
// xplaineer-plasmo/components/AnalysisView.tsx
import React from "react"
import Markdown from "markdown-to-jsx"
import CreditErrorModal from "./CreditErrorModal"

interface QuestionState {
  id: string
  text: string
  answer: string
  loading: boolean
  error: string
}

interface ModelInfo {
  displayName?: string
  provider?: string
}

interface AnalysisViewProps {
  user: any
  isLoading: boolean
  analysis: string
  loading: boolean
  error: string
  showCreditError: boolean
  category: string
  modelInfo: ModelInfo | null
  questions: Array<QuestionState>
  showQuestionInput: boolean
  newQuestion: string
  showDebug: boolean
  isRtl: boolean
  userLanguage: string
  feedbackOpen: boolean
  feedbackEmail: string
  feedbackMessage: string
  feedbackStatus: string
  chosenModelDisplay: string
  modelFallbackMessage: string
  modelFallbackMessage2: string
  setShowQuestionInput: (v: boolean) => void
  setNewQuestion: (v: string) => void
  handleSendQuestion: () => void
  setShowDebug: (v: boolean) => void
  setShowCreditError: (v: boolean) => void
  setFeedbackOpen: (v: boolean) => void
  setFeedbackEmail: (v: string) => void
  setFeedbackMessage: (v: string) => void
  setFeedbackStatus: (v: string) => void
  viewContext?: "tab" | "sidepanel"
}

function sanitizeLottiePlayerTags(markdown: string): string {
  // Remove <lottie>...</lottie> and <player>...</player> blocks (non-greedy)
  markdown = markdown.replace(/<lottie[\s\S]*?<\/lottie>/gi, "");
  markdown = markdown.replace(/<player[\s\S]*?<\/player>/gi, "");
  // Remove self-closing or empty tags
  markdown = markdown.replace(/<lottie\s*\/?>/gi, "");
  markdown = markdown.replace(/<player\s*\/?>/gi, "");
  return markdown;
}

const AnalysisView: React.FC<AnalysisViewProps> = ({
  user,
  isLoading,
  analysis,
  loading,
  error,
  showCreditError,
  category,
  modelInfo,
  questions,
  showQuestionInput,
  newQuestion,
  showDebug,
  isRtl,
  userLanguage,
  feedbackOpen,
  feedbackEmail,
  feedbackMessage,
  feedbackStatus,
  chosenModelDisplay,
  modelFallbackMessage,
  modelFallbackMessage2,
  setShowQuestionInput,
  setNewQuestion,
  handleSendQuestion,
  setShowDebug,
  setShowCreditError,
  setFeedbackOpen,
  setFeedbackEmail,
  setFeedbackMessage,
  setFeedbackStatus,
  viewContext
}) => {
  // Always render UI, even while loading/auth
  return (
    <>
      {/* Login message */}
      {!user && (
        <div className="container mx-auto p-4 max-w-4xl">
          <header className="flex justify-between items-center mb-6">
            <h1
              className="text-2xl font-bold"
              style={{ color: "var(--color-text)" }}>
              {`${process.env.PLASMO_PUBLIC_EXTENSION_NAME || "Xplaineer"} Analysis`}
            </h1>
          </header>
          <div className="flex flex-col items-center justify-center h-64">
            <p className="text-xl" style={{ color: "var(--color-text)" }}>
              Please log in first to use this feature. Click the extensions menu
              (might look like a puzzle piece) and click the pin for{" "}
              {process.env.PLASMO_PUBLIC_EXTENSION_NAME} - then you can click
              the icon and see the login popup.
            </p>
          </div>
        </div>
      )}

      {/* Main content */}
      {user && (
        <div className="container mx-auto p-4">
          {!!error && (
            <div className="error-banner" style={{
              background: "#fee2e2",
              color: "#b91c1c",
              border: "1px solid #fca5a5",
              borderRadius: "6px",
              padding: "12px 18px",
              marginBottom: "18px",
              fontWeight: 500
            }}>
              <strong>Error:</strong> {error}
            </div>
          )}
          <header className="flex justify-between items-center mb-6">
            <div className="flex flex-row items-center flex-wrap gap-4">
              <h1
                className="text-2xl font-bold mb-0"
                style={{ color: "var(--color-text)" }}>
                {`${process.env.PLASMO_PUBLIC_EXTENSION_NAME || "Xplaineer"} Analysis`}
              </h1>
              {/* Ask Question button inline for sidepanel, only after analysis is done */}
              {viewContext === "sidepanel" && !loading && analysis && (
                <button
                  onClick={() => {
                    setShowQuestionInput(true)
                    window.scrollTo({ top: 0, behavior: "smooth" })
                  }}
                  className="px-4 py-2 rounded-lg transition-colors duration-200 ml-2"
                  style={{
                    backgroundColor: "var(--color-button-primary)",
                    color: "var(--color-button-text)",
                    whiteSpace: "nowrap"
                  }}>
                  Ask Question
                </button>
              )}
            </div>
            {modelInfo && (
              <div
                className="px-3 py-1 rounded-full text-sm flex flex-col"
                style={{
                  backgroundColor: "var(--color-background2)",
                  color: "var(--color-text)",
                  minWidth: "180px",
                  fontWeight: 200,
                  fontSize: "0.75rem"
                }}>
                <div className="flex items-center">
                  <span style={{ marginRight: "0.5rem" }}>🤖</span>
                  {modelInfo.displayName
                    ? modelInfo.displayName
                    : typeof modelInfo === "string"
                      ? modelInfo
                      : "Model"}
                  {modelInfo.provider && (
                    <span style={{ marginLeft: "0.5rem", color: "var(--color-secondary)", fontWeight: 200 }}>
                      ({modelInfo.provider})
                    </span>
                  )}
                </div>
                {category && (
                  <div
                    className="flex items-center"
                    style={{
                      marginTop: "0.5rem",
                      alignSelf: "flex-start",
                      background: "var(--color-badge-bg, #e5e7eb)",
                      color: "var(--color-badge-text, #374151)",
                      borderRadius: "999px",
                      padding: "0.15em 0.75em",
                      fontSize: "0.75rem",
                      fontWeight: 200,
                      letterSpacing: "0.01em"
                    }}>
                    <span style={{ marginRight: "0.4em" }}>🏷️</span>
                    {category}
                  </div>
                )}
              </div>
            )}
          </header>

          {showQuestionInput && (
            <div
              className="mb-6 p-4 rounded-lg"
              style={{ backgroundColor: "var(--color-background)" }}>
              <textarea
                value={newQuestion}
                onChange={(e) => setNewQuestion(e.target.value)}
                placeholder="Ask a question about this content..."
                className="w-full p-2 mb-2 rounded-lg"
                style={{
                  backgroundColor: "var(--color-background)",
                  color: "var(--color-text)",
                  border: "1px solid var(--color-secondary)"
                }}
                rows={3}
                autoFocus
              />
              <div className="flex justify-end space-x-2">
                <button
                  onClick={() => setShowQuestionInput(false)}
                  className="px-4 py-2 rounded-lg"
                  style={{
                    backgroundColor: "var(--color-button-secondary)",
                    color: "var(--color-button-text)"
                  }}>
                  Cancel
                </button>
                <button
                  onClick={handleSendQuestion}
                  className="px-4 py-2 rounded-lg"
                  style={{
                    backgroundColor: "var(--color-button-primary)",
                    color: "var(--color-button-text)"
                  }}>
                  Send Question
                </button>
              </div>
            </div>
          )}

          {/* Move Show Debug Info button and debug info to bottom */}

          {questions.length > 0 && (
            <div className="mb-6 space-y-4">
              {questions.map((question) => (
                <div
                  key={question.id}
                  className="p-4 rounded-lg"
                  style={{ backgroundColor: "var(--color-background)" }}
                  dir={isRtl ? "rtl" : "ltr"}
                >
                  <div
                    className="font-medium mb-2"
                    style={{ color: "var(--color-text)" }}>
                    <strong>Q:</strong> {question.text}
                  </div>
                  {question.error ? (
                    <div style={{ color: "var(--color-primary)" }}>
                      {question.error}
                    </div>
                  ) : (
                    <>
                      <div
                        className="prose prose-invert"
                        style={{ color: "var(--color-text)" }}
                      >
                        <Markdown
                          options={{
                            forceBlock: true
                          }}
                        >
                          {sanitizeLottiePlayerTags(question.answer)}
                        </Markdown>
                      </div>
                      {question.loading && (
                        <div style={{ color: "var(--color-text)" }}>
                          <strong className="thinking-indicator thinking-indicator-large">
                            <span className="thinking-letter">T</span>
                            <span className="thinking-letter">h</span>
                            <span className="thinking-letter">i</span>
                            <span className="thinking-letter">n</span>
                            <span className="thinking-letter">k</span>
                            <span className="thinking-letter">i</span>
                            <span className="thinking-letter">n</span>
                            <span className="thinking-letter">g</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                            <span className="thinking-dot">.</span>
                          </strong>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-64">
              <div
                className="animate-spin rounded-full h-12 w-12 border-b-2"
                style={{ borderColor: "var(--color-primary)" }}></div>
              <p className="mt-4" style={{ color: "var(--color-text)" }}>
                Analyzing text...
              </p>
            </div>
          )}

          <CreditErrorModal
            isOpen={showCreditError}
            onClose={() => setShowCreditError(false)}
          />

          {showCreditError && (
            <div style={{ display: "none" }}>
              Credit Error Modal should be visible
            </div>
          )}

          {analysis && (
            <div
              className="prose max-w-none p-4 rounded-lg shadow"
              style={{ backgroundColor: "var(--color-background2)" }}
              dir={isRtl ? "rtl" : "ltr"}
            >
              <div className="prose prose-invert">
                <Markdown
                  options={{
                    forceBlock: true
                  }}
                >
                  {sanitizeLottiePlayerTags(analysis)}
                </Markdown>
              </div>
            </div>
          )}

          {!loading && analysis && (
            viewContext === "sidepanel" ? (
              <div className="space-x-2 mt-6 flex justify-end">
                <button
                  onClick={() => setFeedbackOpen(true)}
                  className="px-4 py-2 rounded-lg transition-colors duration-200"
                  style={{
                    backgroundColor: "var(--color-button-secondary)",
                    color: "var(--color-button-text)"
                  }}>
                  Feedback
                </button>
              </div>
            ) : (
              <div className="fixed top-4 right-4 space-x-2 z-50 transition-all duration-200 bg-opacity-80 hover:bg-opacity-100">
                <button
                  onClick={() => {
                    setShowQuestionInput(true)
                    window.scrollTo({ top: 0, behavior: "smooth" })
                  }}
                  className="px-4 py-2 rounded-lg transition-colors duration-200 backdrop-blur-sm"
                  style={{
                    backgroundColor: "var(--color-button-primary)",
                    color: "var(--color-button-text)"
                  }}>
                  Ask Question
                </button>
                <button
                  onClick={() => setFeedbackOpen(true)}
                  className="px-4 py-2 rounded-lg transition-colors duration-200 backdrop-blur-sm"
                  style={{
                    backgroundColor: "var(--color-button-secondary)",
                    color: "var(--color-button-text)"
                  }}>
                  Feedback
                </button>
              </div>
            )
          )}

          {feedbackOpen && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div
                className="p-6 rounded-lg max-w-md w-full"
                style={{ backgroundColor: "var(--color-background)" }}>
                <h2
                  className="text-xl font-bold mb-4"
                  style={{ color: "var(--color-text)" }}>
                  Send Feedback
                </h2>
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  setFeedbackStatus("Sending...");
                  // Feedback logic should be handled in parent for full separation
                }}>
                  <input
                    type="email"
                    placeholder="Your email"
                    value={feedbackEmail}
                    onChange={(e) => setFeedbackEmail(e.target.value)}
                    className="w-full mb-4 p-2 border rounded"
                    style={{
                      backgroundColor: "var(--color-background)",
                      color: "var(--color-text)"
                    }}
                    required
                  />
                  <textarea
                    placeholder="Your message"
                    value={feedbackMessage}
                    onChange={(e) => setFeedbackMessage(e.target.value)}
                    className="w-full mb-4 p-2 border rounded h-32"
                    style={{
                      backgroundColor: "var(--color-background)",
                      color: "var(--color-text)"
                    }}
                    required
                  />
                  {feedbackStatus && (
                    <div className="mb-4 text-center" style={{ color: feedbackStatus.includes('Error') || feedbackStatus.includes('Failed') ? 'red' : 'green' }}>
                      {feedbackStatus}
                    </div>
                  )}
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => {
                        setFeedbackOpen(false)
                        setFeedbackStatus('')
                        setFeedbackEmail('')
                        setFeedbackMessage('')
                      }}
                      type="button"
                      className="px-4 py-2"
                      style={{ color: "var(--color-text)" }}>
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 rounded"
                      style={{
                        backgroundColor: "var(--color-button-primary)",
                        color: "var(--color-button-text)"
                      }}>
                      Send
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Show Debug Info button and debug info at the bottom */}
          <div className="mt-8 flex flex-col items-end">
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="mb-2 px-4 py-2 rounded-lg"
              style={{
                backgroundColor: "var(--color-button-primary)",
                color: "var(--color-button-text)"
              }}>
              {showDebug ? "Hide Debug Info" : "Show Debug Info"}
            </button>
            {showDebug && (
              <>
                <button
                  onClick={() => {
                    setShowCreditError(true)
                  }}
                  className="ml-2 mb-2 px-4 py-2 rounded-lg"
                  style={{
                    backgroundColor: "var(--color-button-secondary)",
                    color: "var(--color-button-text)"
                  }}>
                  Test Credit Error Modal
                </button>
                <div className="mb-4 w-full">
                  <strong>Debug Info:</strong>
                  <pre
                    className="p-2 rounded"
                    style={{ backgroundColor: "var(--color-background)" }}>
                    {JSON.stringify(
                      {
                        hasAnalysis: analysis.length > 0,
                        analysisLength: analysis.length,
                        loading: loading,
                        hasError: !!error,
                        showCreditError: showCreditError,
                        category: category,
                        questions: questions.length,
                        showQuestionInput: showQuestionInput,
                        modelInfo: modelInfo,
                        language: userLanguage,
                        isRtl: isRtl
                      },
                      null,
                      2
                    )}
                  </pre>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}

export default AnalysisView

</code>

storage\theme.ts:
<code>
// storage/theme.ts
import { Storage } from "@plasmohq/storage"

export interface ThemeSettings {
  theme: "light" | "dark" | "ocean" | "business" | "sunset" | "forest" | "midnightBloom" | "cyberpunkNeon" | "volcanicAsh" | "deepSea" | "enchantedForest" | "arcticNight" | "retroWave" | "gothicManor" | "cosmicDust" | "desertMirage" | "emeraldCity" | "rubyGlow" | "amethystHaze" | "obsidian" | "goldenHour" | "rainbowSpectrum" | "rainbowSpectrumv2" | "cosmicLatte" | "synthwaveSunset" | "emeraldTablet" | "paper" | "twilight" | "highContrastBlueYellow" | "monochromePlus" | "custom"
  fontFamily: string
  fontWeight: number // 100-900, with 400 being normal and 700 being bold
  fontSize: {
    body: string
    h1: string
    h2: string
    h3: string
  }
  colors: {
    background: string
    background2: string
    text: string
    primary: string
    secondary: string
    border: string
    buttonHover: string
    button: {
      primary: string
      secondary: string
      text: string
    }
    headings: {
      h1: string
      h2: string
      h3: string
    }
    emphasis: string // For <em> tags (italics)
    emphasisGradient: { // <-- UPDATED TYPE
      color1: string,
      color2: string,
      color3: string,
    }
    bold: string // For <strong> tags
    citation: string // For citation spans
    liteHumor: string // For spans styled with pink (Lite Humor)
  }
  spacing: {
    lineHeight: string
    paragraphSpacing: string
    listSpacing: string
    listIndent: string
  }
}

// Further adjusted colors for stronger differences in themes
const darkTheme: ThemeSettings = {
  theme: "dark",
  fontFamily: "Noto Sans",
  fontWeight: 400,
  fontSize: {
    body: "15px",
    h1: "1.8em",
    h2: "1.5em",
    h3: "1.3em"
  },
  colors: {
    emphasis: "#2a3f7c", // Darker blue for better contrast
    emphasisGradient: { // <-- UPDATED STRUCTURE
      color1: "#5A9BD3",
      color2: "#FFFFFF",
      color3: "#5A9BD3"
    },
    bold: "#d02b2b", // More vibrant red
    citation: "#90CAF9", // Light Blue
    liteHumor: "#F48FB1", // Softer Pink
    background: "#0c0c0c", // Even darker background
    background2: "#1e1e1e", // Slightly lighter secondary background
    text: "#E0E0E0", // Brighter text for contrast
    primary: "#0077cc", // More vibrant primary
    secondary: "#00BFA5", // More distinct secondary
    border: "#4a4a4a", // Slightly lighter border
    buttonHover: "#bce7e5", // More noticeable hover color
    button: {
      primary: "#0056b3", // Stronger primary button
      secondary: "#2E7D32", // Stronger secondary button
      text: "#FFFFFF" // Pure white button text
    },
    headings: {
      h1: "#8A2BE2", // More vibrant purple
      h2: "#00BFA5", // Match secondary with stronger tone
      h3: "#558B2F" // More distinct green
    }
  },
  spacing: {
    lineHeight: "1.3",
    paragraphSpacing: "1.2rem",
    listSpacing: "0.5rem",
    listIndent: "0.2rem"
  }
}

const lightTheme: ThemeSettings = {
  theme: "light",
  fontFamily: "Noto Sans",
  fontWeight: 400,
  fontSize: {
    body: "15px",
    h1: "1.8em",
    h2: "1.5em",
    h3: "1.3em"
  },
  colors: {
    emphasis: "#005F6A", // Darker teal for better contrast
    emphasisGradient: { // <-- UPDATED STRUCTURE
      color1: "#FF7F50",
      color2: "#FFFFFF",
      color3: "#FF7F50"
    },
    bold: "#1FE6A2", // More vibrant green
    citation: "#FF8A65", // Coral/Orange
    liteHumor: "#4FC3F7", // Light Blue
    background: "#FFFFFF", // Pure white for clarity
    background2: "#F5F5F5", // Slightly lighter secondary background
    text: "#121212", // Darker text for contrast
    primary: "#1FE6A2", // More vibrant primary
    secondary: "#005F6A", // More distinct secondary
    border: "#C0C0C0", // Slightly darker border
    buttonHover: "#17BFA3", // More noticeable hover color
    button: {
      primary: "#007ACC", // Stronger primary button
      secondary: "#2E7D32", // Stronger secondary button
      text: "#FFFFFF" // Pure white button text
    },
    headings: {
      h1: "#0D47A1", // Stronger blue
      h2: "#2E7D32", // Match secondary with stronger tone
      h3: "#1B5E20" // More distinct green
    }
  },
  spacing: {
    lineHeight: "1.3",
    paragraphSpacing: "1.2rem",
    listSpacing: "0.5rem",
    listIndent: "0.2rem"
  }
}

const oceanTheme: ThemeSettings = {
  ...darkTheme,
  theme: "ocean",
  fontWeight: 400,
  colors: {
    ...darkTheme.colors,
    citation: "#FFCC80", // Light Orange/Sand
    liteHumor: "#80CBC4", // Teal/Aqua
    background: "#0F1E2E", // Darker navy for depth
    background2: "#1C3A50", // More distinct secondary background
    emphasis: "#1A6FAD", // Stronger blue
    emphasisGradient: { // <-- UPDATED STRUCTURE
      color1: "#009ACD",
      color2: "#FFFFFF",
      color3: "#009ACD"
    },
    text: "#E0F0F5", // Brighter text for clarity
    primary: "#1A6FAD", // More vibrant primary
    secondary: "#1DB954", // More distinct secondary
    border: "#2C4A5E", // Slightly lighter border
    buttonHover: "#0F5F8B", // More noticeable hover color
    button: {
      primary: "#0F6F9C", // Stronger primary button
      secondary: "#1AAE4A", // Stronger secondary button
      text: "#FFFFFF" // Pure white button text
    },
    headings: {
      h1: "#1F8EDF", // Stronger blue
      h2: "#1DB954", // Match secondary with stronger tone
      h3: "#E53935" // More distinct red
    }
  }
}

class ThemeStorage {
  private storage: Storage
  private predefinedThemes: { [key: string]: ThemeSettings }

  constructor() {
    this.storage = new Storage()
    this.predefinedThemes = {
      dark: darkTheme,
      light: lightTheme,
      ocean: oceanTheme,
      // --- BUSINESS/WORK THEME ---
      business: {
        ...lightTheme,
        theme: "business",
        fontFamily: "Inter, Segoe UI, Arial, sans-serif",
        fontWeight: 400,
        fontSize: {
          body: "15px",
          h1: "2em",
          h2: "1.5em",
          h3: "1.2em"
        },
        colors: {
          ...lightTheme.colors,
          background: "#f7fafd", // very light blue-gray
          background2: "#e9eef3", // slightly darker for cards/headers
          text: "#1a1d1f", // almost black
          primary: "#2563eb", // strong blue
          secondary: "#64748b", // slate gray
          border: "#d1d5db", // light gray
          buttonHover: "#1d4ed8", // darker blue
          button: {
            primary: "#2563eb",
            secondary: "#64748b",
            text: "#ffffff"
          },
          headings: {
            h1: "#1e293b", // dark slate
            h2: "#2563eb", // blue
            h3: "#64748b" // slate gray
          },
          emphasis: "#2563eb",
          emphasisGradient: {
            color1: "#2563eb",
            color2: "#e0e7ef",
            color3: "#2563eb"
          },
          bold: "#1e293b",
          citation: "#0ea5e9", // cyan
          liteHumor: "#fbbf24" // amber
        },
        spacing: {
          lineHeight: "1.4",
          paragraphSpacing: "1.1rem",
          listSpacing: "0.5rem",
          listIndent: "0.2rem"
        }
      },
      sunset: {
        ...darkTheme,
        theme: "sunset",
        fontWeight: 400,
        colors: {
          ...darkTheme.colors,
          citation: "#FFEB3B", // Brighter Yellow
          liteHumor: "#FF8A65", // Coral
          background: "#2c1810",
          background2: "#3d2317",
          emphasis: "#ff5722",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#FFA07A",
            color2: "#FFFFFF",
            color3: "#FFA07A"
          },
          text: "#fff3e0",
          primary: "#ff5722",
          secondary: "#ff9800",
          border: "#4e342e",
          buttonHover: "#f4511e",
          button: {
            primary: "#fa5520",
            secondary: "#ff9800",
            text: "#ffffff"
          },
          headings: {
            h1: "#ff5722",
            h2: "#ff9800",
            h3: "#ffc107"
          }
        },
        spacing: { ...darkTheme.spacing }
      },
      forest: {
        ...darkTheme,
        theme: "forest",
        fontWeight: 400,
        colors: {
          ...darkTheme.colors,
          citation: "#CDDC39", // Lime Green
          liteHumor: "#AED581", // Light Green
          background: "#1b2819",
          background2: "#2c3e2b",
          emphasis: "#4caf50",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#90EE90",
            color2: "#FFFFFF",
            color3: "#90EE90"
          },
          text: "#e8f5e9",
          primary: "#4caf50",
          secondary: "#8bc34a",
          border: "#33691e",
          buttonHover: "#43a047",
          button: {
            primary: "#45a549",
            secondary: "#83bc41",
            text: "#ffffff"
          },
          headings: {
            h1: "#51b354",
            h2: "#93c94f",
            h3: "#cddc39"
          }
        },
        spacing: { ...darkTheme.spacing }
      },
      midnightBloom: {
        ...darkTheme,
        theme: "midnightBloom",
        fontWeight: 400,
        fontFamily: "Snowburst One",
        fontSize: { body: "17.97px", h1: "2.16em", h2: "1.79em", h3: "1.55em" },
        spacing: { lineHeight: "1.55", paragraphSpacing: "1.43rem", listSpacing: "0.61rem", listIndent: "0.24rem" },
        colors: {
          ...darkTheme.colors,
          citation: "#BA68C8", // Light Purple
          liteHumor: "#4DB6AC", // Teal
          background: "#1a1a2e",
          background2: "#0b0b1e",
          text: "#e0e0ff",
          primary: "#18e74c",
          secondary: "#9471a2",
          border: "#4a4a6e",
          buttonHover: "#b72856",
          button: { primary: "#3747be", secondary: "#683fa6", text: "#1cca3e" },
          headings: { h1: "#d04070", h2: "#964ab5", h3: "#a076d6" },
          emphasis: "#a076d6",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#e0e0ff",
            color2: "#c73866",
            color3: "#e0e0ff"
          },
          bold: "#ff6b6b"
        }
      },
      cyberpunkNeon: {
        theme: "cyberpunkNeon",
        fontFamily: "Manrope",
        fontWeight: 400,
        fontSize: {
          body: "17.27px",
          h1: "2.31em",
          h2: "2.37em",
          h3: "2.05em"
        },
        colors: {
          emphasis: "#316d26",
          emphasisGradient: {
            color1: "#ff0000",
            color2: "#ffd500",
            color3: "#eeff00"
          },
          bold: "#acb12b",
citation: "#FF00FF",
          liteHumor: "#1fe07c",
          background: "#0f0f0f",
          background2: "#1f1f1f",
          text: "#e0e0e0",
          primary: "#04dcdc",
          secondary: "#ff00ff",
          border: "#333333",
          buttonHover: "#0025db",
          button: {
            primary: "#8bd68a",
            secondary: "#7728b8",
            text: "#121212"
          },
          headings: {
            h1: "#ff3f0f",
            h2: "#0f5fff",
            h3: "#ffb514"
          }
        },
        spacing: {
          lineHeight: "1.46",
          paragraphSpacing: "1.22rem",
          listSpacing: "0.89rem",
          listIndent: "0.35rem"
        }
      },
      volcanicAsh: {
        ...darkTheme,
        theme: "volcanicAsh",
        fontWeight: 400,
        fontFamily: "Forum",
        colors: {
          ...darkTheme.colors,
          citation: "#FF7043", // Orange-Red
          liteHumor: "#FFCA28", // Amber
          background: "#212121",
          background2: "#313131",
          text: "#d7d7d7",
          primary: "#ff4500",
          secondary: "#dc143c",
          border: "#424242",
          buttonHover: "#e03500",
          button: { ...darkTheme.colors.button, primary: "#fa4000", secondary: "#d11035", text: "#ffffff" },
          headings: { h1: "#ff4a0a", h2: "#e41943", h3: "#ff8c00" },
          emphasis: "#ff8c00",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#d7d7d7",
            color2: "#ff4500",
            color3: "#d7d7d7"
          },
          bold: "#b22222"
        }
      },
      deepSea: {
        ...darkTheme,
        theme: "deepSea",
        fontWeight: 400,
        colors: {
          ...darkTheme.colors,
          citation: "#90CAF9", // Light Blue
          liteHumor: "#80DEEA", // Cyan/Aqua
          background: "#001f3f",
          background2: "#003366",
          text: "#add8e6",
          primary: "#00ced1",
          secondary: "#20b2aa",
          border: "#004080",
          buttonHover: "#00b8c2",
          button: { ...darkTheme.colors.button, primary: "#00c0c4", secondary: "#1ea8a0", text: "#ffffff" },
          headings: { h1: "#10d8db", h2: "#30bbb3", h3: "#7fffd4" },
          emphasis: "#7fffd4",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#add8e6",
            color2: "#00ced1",
            color3: "#add8e6"
          },
          bold: "#32cd32"
        }
      },
      enchantedForest: {
        ...darkTheme,
        theme: "enchantedForest",
        fontWeight: 400,
        fontFamily: "Pangolin",
        colors: {
          ...darkTheme.colors,
          citation: "#CE93D8", // Light Purple
          liteHumor: "#FFAB91", // Light Peach
          background: "#14281d",
          background2: "#24382d",
          text: "#d0e0d5",
          primary: "#6a0dad",
          secondary: "#daa520",
          border: "#34483d",
          buttonHover: "#5a0c9d",
          button: { ...darkTheme.colors.button, primary: "#650aa5", secondary: "#d19f15", text: "#ffffff" },
          headings: { h1: "#7518bf", h2: "#e5b030", h3: "#8fbc8f" },
          emphasis: "#8fbc8f",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#d0e0d5",
            color2: "#6a0dad",
            color3: "#d0e0d5"
          },
          bold: "#ff69b4"
        }
      },
      arcticNight: {
        ...darkTheme,
        theme: "arcticNight",
        fontWeight: 400,
        fontFamily: "Be Vietnam Pro",
        colors: {
          ...darkTheme.colors,
          citation: "#B0BEC5", // Blue Grey
          liteHumor: "#CFD8DC", // Lighter Blue Grey
          background: "#1c2331",
          background2: "#2c3341",
          text: "#e0f2f7",
          primary: "#ffffff",
          secondary: "#87ceeb",
          border: "#3c4351",
          buttonHover: "#f0f0f0",
          button: { ...darkTheme.colors.button, primary: "#87ceeb", secondary: "#b0c4de", text: "#1c2331" },
          headings: { h1: "#ffffff", h2: "#87ceeb", h3: "#b0c4de" },
          emphasis: "#b0c4de",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#e0f2f7",
            color2: "#ffffff",
            color3: "#e0f2f7"
          },
          bold: "#add8e6"
        }
      },
      retroWave: {
        ...darkTheme,
        theme: "retroWave",
        fontWeight: 400,
        fontFamily: "Macondo Swash Caps",
        colors: {
          ...darkTheme.colors,
          citation: "#FFEB3B", // Yellow
          liteHumor: "#00BCD4", // Cyan
          background: "#2c003e",
          background2: "#3c104e",
          text: "#f0e0ff",
          primary: "#ff00cc",
          secondary: "#00f2ff",
          border: "#4c205e",
          buttonHover: "#e600b8",
          button: { ...darkTheme.colors.button, primary: "#ff00cc", secondary: "#00f2ff" },
          headings: { h1: "#ff00cc", h2: "#00f2ff", h3: "#ff8c00" },
          emphasis: "#ff8c00",
          emphasisGradient: { // <-- UPDATED STRUCTURE (Original only had 2 colors, added text color in middle)
            color1: "#ff00cc",
            color2: "#f0e0ff", // Text color as middle stop
            color3: "#00f2ff"
            // Alternative: repeat first/last: { color1: "#ff00cc", color2: "#00f2ff", color3: "#ff00cc" }
          },
          bold: "#fff000"
        }
      },
      gothicManor: {
        theme: "gothicManor",
        fontFamily: "Gidole",
        fontWeight: 400,
        fontSize: {
          body: "17.96px",
          h1: "1.78em",
          h2: "1.48em",
          h3: "1.29em"
        },
        colors: {
          emphasis: "#a9a9a9",
          emphasisGradient: {
            color1: "#737373",
            color2: "#ffffff",
            color3: "#bdbdbd"
          },
          bold: "#f2f2f2",
          citation: "#D2B48C",
          liteHumor: "#8fbca5",
          background: "#1a1a1a",
          background2: "#2a2a2a",
          text: "#c0c0c0",
          primary: "#8b0000",
          secondary: "#a9a9a9",
          border: "#3a3a3a",
          buttonHover: "#930b5a",
          button: {
            primary: "#800000",
            secondary: "#888888",
            text: "#ffffff"
          },
          headings: {
            h1: "#990000",
            h2: "#b6b6b6",
            h3: "#777777"
          }
        },
        spacing: {
          lineHeight: "1.29",
          paragraphSpacing: "1.19rem",
          listSpacing: "0.5rem",
          listIndent: "0.2rem"
        }
      },
      cosmicDust: {
        ...darkTheme,
        theme: "cosmicDust",
        fontWeight: 400,
        fontFamily: "Jura",
        colors: {
          ...darkTheme.colors,
          citation: "#7986CB", // Indigo Light
          liteHumor: "#64B5F6", // Blue Light
          background: "#050510",
          background2: "#151520",
          text: "#e0e0f0",
          primary: "#4d4dff",
          secondary: "#9d4dff",
          border: "#252530",
          buttonHover: "#3d3dff",
          button: { ...darkTheme.colors.button, primary: "#4545f5", secondary: "#9545f5", text: "#ffffff" },
          headings: { h1: "#5353ff", h2: "#a353ff", h3: "#f0f0ff" },
          emphasis: "#ffffff",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#e0e0f0",
            color2: "#4d4dff",
            color3: "#e0e0f0"
          },
          bold: "#ff4da6"
        }
      },
      desertMirage: {
        ...darkTheme,
        theme: "desertMirage",
        fontWeight: 400,
        fontFamily: "Handlee",
        colors: {
          ...darkTheme.colors,
          citation: "#FFCCBC", // Light Peach/Orange
          liteHumor: "#BCAAA4", // Brownish Grey
          background: "#3e2723",
          background2: "#4e342e",
          text: "#fff3e0",
          primary: "#ff9800",
          secondary: "#8d6e63",
          border: "#5d4037",
          buttonHover: "#f57c00",
          button: { ...darkTheme.colors.button, primary: "#ff9800", secondary: "#8d6e63" },
          headings: { h1: "#ff9800", h2: "#8d6e63", h3: "#03a9f4" },
          emphasis: "#03a9f4",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#fff3e0",
            color2: "#ff9800",
            color3: "#fff3e0"
          },
          bold: "#f44336"
        }
      },
      emeraldCity: {
        ...darkTheme,
        theme: "emeraldCity",
        fontWeight: 400,
        fontFamily: "Macondo",
        colors: {
          ...darkTheme.colors,
          citation: "#FFF59D", // Pale Yellow
          liteHumor: "#A5D6A7", // Pale Green
          background: "#003300",
          background2: "#004d00",
          text: "#e0ffe0",
          primary: "#00e600",
          secondary: "#ffd700",
          border: "#006600",
          buttonHover: "#00cc00",
          button: { ...darkTheme.colors.button, primary: "#00e600", secondary: "#ffd700" },
          headings: { h1: "#00e600", h2: "#ffd700", h3: "#b8860b" },
          emphasis: "#b8860b",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#e0ffe0",
            color2: "#00e600",
            color3: "#e0ffe0"
          },
          bold: "#ffffff"
        }
      },
      rubyGlow: {
        ...darkTheme,
        theme: "rubyGlow",
        fontWeight: 400,
        fontFamily: "Griffy",
        colors: {
          ...darkTheme.colors,
          citation: "#FFCDD2", // Pale Red
          liteHumor: "#F8BBD0", // Pale Pink
          background: "#3b0000",
          background2: "#5c0000",
          text: "#ffe0e0",
          primary: "#e0115f",
          secondary: "#ff69b4",
          border: "#7c0000",
          buttonHover: "#c7004f",
          button: { ...darkTheme.colors.button, primary: "#e0115f", secondary: "#ff69b4" },
          headings: { h1: "#e0115f", h2: "#ff69b4", h3: "#ffb6c1" },
          emphasis: "#ffb6c1",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#ffe0e0",
            color2: "#e0115f",
            color3: "#ffe0e0"
          },
          bold: "#ffffff"
        }
      },
      amethystHaze: {
        ...darkTheme,
        theme: "amethystHaze",
        fontWeight: 400,
        fontFamily: "Almendra",
        colors: {
          ...darkTheme.colors,
          citation: "#D1C4E9", // Light Purple/Lavender
          liteHumor: "#B39DDB", // Medium Purple/Lavender
          background: "#301934",
          background2: "#48284a",
          text: "#e6e6fa",
          primary: "#9966cc",
          secondary: "#c0c0c0",
          border: "#60306a",
          buttonHover: "#8a56b9",
          button: { ...darkTheme.colors.button, primary: "#8956c7", secondary: "#b8b8c2", text: "#ffffff" },
          headings: { h1: "#a36adf", h2: "#bab8c7", h3: "#d8bfd8" },
          emphasis: "#d8bfd8",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#e6e6fa",
            color2: "#9966cc",
            color3: "#e6e6fa"
          },
          bold: "#f0f0f5"
        }
      },
      obsidian: {
        ...darkTheme,
        theme: "obsidian",
        fontWeight: 400,
        fontFamily: "Wix Madefor Display",
        colors: {
          ...darkTheme.colors,
          citation: "#9E9E9E", // Grey
          liteHumor: "#607D8B", // Blue Grey
          background: "#0a0a0a",
          background2: "#1a1a1a",
          text: "#f0f0f0",
          primary: "#00bfff",
          secondary: "#f5f5f7",
          border: "#2a2a2a",
          buttonHover: "#00aeee",
          button: { ...darkTheme.colors.button, primary: "#0ab5f5", secondary: "#c4c4cc", text: "#0a0a0a" },
          headings: { h1: "#19c8ff", h2: "#e6e6e9", h3: "#ccccdd" },
          emphasis: "#f5f5f7",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#f0f0f0",
            color2: "#00bfff",
            color3: "#f0f0f0"
          },
          bold: "#ff5511"
        }
      },
      goldenHour: {
        ...darkTheme,
        theme: "goldenHour",
        fontWeight: 400,
        fontFamily: "Unkempt",
        colors: {
          ...darkTheme.colors,
          citation: "#FFE082", // Pale Yellow/Gold
          liteHumor: "#FFCC80", // Pale Orange/Gold
          background: "#2e1a00",
          background2: "#402500",
          text: "#fff8e1",
          primary: "#ffab00",
          secondary: "#ffca28",
          border: "#533000",
          buttonHover: "#ff9100",
          button: { ...darkTheme.colors.button, primary: "#ffab00", secondary: "#ffca28" },
          headings: { h1: "#ffab00", h2: "#ffca28", h3: "#ffd54f" },
          emphasis: "#ffd54f",
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#fff8e1",
            color2: "#ffab00",
            color3: "#fff8e1"
          },
          bold: "#e65100"
        }
      },
      rainbowSpectrum: {
        ...darkTheme,
        theme: "rainbowSpectrum",
        fontWeight: 400,
        fontFamily: "'Comic Sans MS', cursive, sans-serif", // A bit playful
        fontSize: { body: "16px", h1: "2em", h2: "1.7em", h3: "1.4em" },
        colors: {
          ...darkTheme.colors,
          citation: "#FFEB3B", // Yellow
          liteHumor: "#FF4081", // Pink Accent
          background: "#1a1a1a",
          background2: "#2c2c2c",
          text: "#ffffff",
          primary: "#FF0000", // Red
          secondary: "#0000FF", // Blue
          border: "#444444",
          buttonHover: "#e6e6e6",
          button: { primary: "#FF0000", secondary: "#0000FF", text: "#ffffff" },
          headings: {
            h1: "#FF00FF", // Magenta
            h2: "#00FF00", // Green
            h3: "#FFFF00" // Yellow
          },
          emphasis: "#FFA500", // Orange
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#FF0000",
            color2: "#FFFF00",
            color3: "#00FF00"
          },
          bold: "#00FFFF" // Cyan
        }
      },
      rainbowSpectrumv2: {
        theme: "rainbowSpectrumv2",
        fontFamily: "Quicksand",
        fontWeight: 100,
        fontSize: {
          body: "15.36px",
          h1: "1.93em",
          h2: "1.64em",
          h3: "1.34em"
        },
        colors: {
          emphasis: "#FFA500",
          emphasisGradient: {
            color1: "#FF0000",
            color2: "#FFFF00",
            color3: "#00FF00"
          },
          bold: "#00FFFF",
          citation: "#FFEB3B",
          liteHumor: "#FF4081",
          background: "#1a1a1a",
          background2: "#2c2c2c",
          text: "#ffffff",
          primary: "#FF0000",
          secondary: "#0000FF",
          border: "#444444",
          buttonHover: "#e6e6e6",
          button: {
            primary: "#FF0000",
            secondary: "#0000FF",
            text: "#ffffff"
          },
          headings: {
            h1: "#FF00FF",
            h2: "#00FF00",
            h3: "#FFFF00"
          }
        },
        spacing: {
          lineHeight: "1.25",
          paragraphSpacing: "1.14rem",
          listSpacing: "0.49rem",
          listIndent: "0.19rem"
        }
      },
      highContrastBlueYellow: {
        theme: "highContrastBlueYellow",
        fontFamily: "Original Surfer",
        fontWeight: 100,
        fontSize: {
          body: "18.15px",
          h1: "2.18em",
          h2: "1.81em",
          h3: "1.57em"
        },
        colors: {
          emphasis: "#FFEB3B",
          emphasisGradient: {
            color1: "#02f26a",
            color2: "#ffee05",
            color3: "#ff0505"
          },
          bold: "#817979",
          citation: "#3de8ff",
          liteHumor: "#c250f7",
          background: "#000000",
          background2: "#1a1a1a",
          text: "#FFFFFF",
          primary: "#03A9F4",
          secondary: "#FFC107",
          border: "#555555",
          buttonHover: "#0288D1",
          button: {
            primary: "#434158",
            secondary: "#51431a",
            text: "#f0f0f0"
          },
          headings: {
            h1: "#FFFFFF",
            h2: "#03A9F4",
            h3: "#FFC107"
          }
        },
        spacing: {
          lineHeight: "1.57",
          paragraphSpacing: "1.45rem",
          listSpacing: "0.61rem",
          listIndent: "0.24rem"
        }
      },
      cosmicLatte: {
        ...lightTheme, // Start with light theme base
        theme: "cosmicLatte",
        fontFamily: "'Garamond', serif",
        fontSize: { body: "16px", h1: "1.9em", h2: "1.6em", h3: "1.4em" },
        colors: {
          ...lightTheme.colors,
          citation: "#BCAAA4", // Light Brown/Grey
          liteHumor: "#B0BEC5", // Blue Grey
          background: "#fdfcf8", // Very light beige
          background2: "#f5f2e9", // Slightly darker beige
          text: "#4b3832", // Dark brown text
          primary: "#8d6e63", // Muted brown-grey
          secondary: "#a1887f", // Lighter brown-grey
          border: "#d7ccc8", // Light grey-brown border
          buttonHover: "#795548", // Darker brown hover
          button: {
            primary: "#8d6e63",
            secondary: "#a1887f",
            text: "#ffffff"
          },
          headings: {
            h1: "#5d4037", // Darkest brown
            h2: "#795548", // Medium brown
            h3: "#8d6e63" // Muted brown-grey (same as primary)
          },
          emphasis: "#a1887f", // Lighter brown-grey (same as secondary)
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#c8b5a6",
            color2: "#ffffff",
            color3: "#c8b5a6"
          },
          bold: "#5d4037" // Darkest brown
        }
      },
      synthwaveSunset: {
        ...darkTheme,
        theme: "synthwaveSunset",
        fontWeight: 400,
        fontFamily: "'Space Grotesk', sans-serif",
        colors: {
          ...darkTheme.colors,
          citation: "#FFEB3B", // Yellow
          liteHumor: "#76FF03", // Lime Green
          background: "#2c0b2e", // Dark purple
          background2: "#3d1f4f", // Slightly lighter purple
          text: "#f0e0ff", // Light lavender text
          primary: "#ff6ac1", // Hot pink
          secondary: "#ffca28", // Bright yellow/orange
          border: "#5a396e", // Muted purple border
          buttonHover: "#e650a1", // Slightly darker pink hover
          button: {
            primary: "#ff6ac1",
            secondary: "#ffca28",
            text: "#2c0b2e" // Dark purple text on buttons
          },
          headings: {
            h1: "#ff6ac1", // Hot pink
            h2: "#ffca28", // Bright yellow/orange
            h3: "#00f2ff" // Cyan accent
          },
          emphasis: "#00f2ff", // Cyan accent
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#ff6ac1",
            color2: "#ffca28",
            color3: "#00f2ff"
          },
          bold: "#f0e0ff" // Light lavender bold
        }
      },
      emeraldTablet: {
        ...darkTheme,
        theme: "emeraldTablet",
        fontWeight: 400,
        fontFamily: "'Gidole', sans-serif",
        colors: {
          ...darkTheme.colors,
          citation: "#FFF9C4", // Very Pale Yellow
          liteHumor: "#C8E6C9", // Very Pale Green
          background: "#0a1f0a", // Very dark green
          background2: "#1a3a1a", // Dark green
          text: "#c0e0c0", // Pale green text
          primary: "#00e600", // Bright emerald green
          secondary: "#ffd700", // Gold accent
          border: "#2a5a2a", // Muted green border
          buttonHover: "#00cc00", // Slightly darker green hover
          button: {
            primary: "#00e600",
            secondary: "#ffd700",
            text: "#0a1f0a" // Dark green text on buttons
          },
          headings: {
            h1: "#00e600", // Bright emerald green
            h2: "#ffd700", // Gold accent
            h3: "#b8860b" // Darker gold
          },
          emphasis: "#b8860b", // Darker gold
          emphasisGradient: { // <-- UPDATED STRUCTURE
            color1: "#00e600",
            color2: "#c0e0c0",
            color3: "#ffd700"
          },
          bold: "#FFFFFF"
        }
      },
      // --- NEW MILD THEMES ---
      paper: {
        ...lightTheme,
        theme: "paper",
        fontWeight: 400,
        fontFamily: "'Merriweather', serif",
        colors: {
          ...lightTheme.colors,
          citation: "#BCAAA4", // Muted Brown/Grey
          liteHumor: "#A5D6A7", // Muted Green
          background: "#fbfaf8", // Off-white paper
          background2: "#f0ede8", // Slightly darker paper texture
          text: "#5d4037", // Dark Sepia/Brown text
          primary: "#8d6e63", // Muted brown
          secondary: "#a1887f", // Lighter muted brown
          border: "#d7ccc8", // Very light brown/grey border
          buttonHover: "#6d4c41", // Darker sepia hover
          button: {
            primary: "#8d6e63",
            secondary: "#a1887f",
            text: "#ffffff"
          },
          headings: {
            h1: "#4e342e", // Darkest sepia
            h2: "#6d4c41", // Medium sepia
            h3: "#8d6e63" // Muted brown (primary)
          },
          emphasis: "#a1887f", // Lighter muted brown (secondary)
          emphasisGradient: {
            color1: "#d7ccc8",
            color2: "#ffffff",
            color3: "#d7ccc8"
          },
          bold: "#4e342e" // Darkest sepia
        }
      },
      twilight: {
        ...darkTheme,
        theme: "twilight",
        fontWeight: 400,
        fontFamily: "Lato",
        colors: {
          ...darkTheme.colors,
          citation: "#9FA8DA", // Muted Indigo
          liteHumor: "#CE93D8", // Muted Purple
          background: "#263238", // Dark Blue Grey
          background2: "#37474F", // Slightly Lighter Blue Grey
          text: "#CFD8DC", // Light Blue Grey text
          primary: "#64B5F6", // Muted Blue
          secondary: "#9575CD", // Muted Purple
          border: "#455A64", // Darker Blue Grey border
          buttonHover: "#42A5F5", // Slightly brighter blue hover
          button: {
            primary: "#64B5F6",
            secondary: "#9575CD",
            text: "#ffffff"
          },
          headings: {
            h1: "#90CAF9", // Lighter Muted Blue
            h2: "#B39DDB", // Lighter Muted Purple
            h3: "#80CBC4" // Muted Teal accent
          },
          emphasis: "#80CBC4", // Muted Teal accent
          emphasisGradient: {
            color1: "#64B5F6",
            color2: "#CFD8DC",
            color3: "#9575CD"
          },
          bold: "#FFFFFF" // White for contrast
        }
      },
      // --- NEW COLORBLIND FRIENDLY THEMES ---
      monochromePlus: { // High Contrast Grayscale + Accent
        ...darkTheme,
        theme: "monochromePlus",
        fontWeight: 400,
        fontFamily: "'Roboto Mono', monospace", // Monospace for distinction
        colors: {
          ...darkTheme.colors,
          citation: "#00BCD4", // Cyan Accent
          liteHumor: "#BDBDBD", // Light Grey
          background: "#121212", // Very Dark Grey
          background2: "#2d2d2d", // Dark Grey
          text: "#F5F5F5", // Very Light Grey / Off-white
          primary: "#00BCD4", // Cyan Accent
          secondary: "#9E9E9E", // Medium Grey
          border: "#424242", // Grey border
          buttonHover: "#00ACC1", // Darker Cyan hover
          button: {
            primary: "#00BCD4",
            secondary: "#757575", // Darker Grey Button
            text: "#000000" // Black text on buttons
          },
          headings: {
            h1: "#FFFFFF", // White
            h2: "#E0E0E0", // Light Grey
            h3: "#BDBDBD" // Lighter Medium Grey
          },
          emphasis: "#00BCD4", // Cyan Accent
          emphasisGradient: {
            color1: "#9E9E9E",
            color2: "#F5F5F5",
            color3: "#9E9E9E"
          },
          bold: "#FFFFFF" // White
        }
      }
      // 'custom' theme is usually dynamically generated/saved, so no definition here
    }
  }

  getThemes(): { [key: string]: ThemeSettings } {
    // Returns the map of predefined theme names to their settings
    return this.predefinedThemes;
  }


  async getThemeSettings(): Promise<ThemeSettings> {
    const settings = await this.storage.get("themeSettings")
    try {
      let parsedSettings: any;
      if (typeof settings === "string") {
        try {
          parsedSettings = JSON.parse(settings);
        } catch (e) {
          console.error("Failed to parse theme settings from string:", e);
          // Fallback to default if parsing fails
          return this.ensureCompleteThemeSettings(this.predefinedThemes.dark);
        }
      } else {
        parsedSettings = settings;
      }

      // If settings are null/undefined or not an object, return default dark theme
      if (!parsedSettings || typeof parsedSettings !== 'object') {
        if (process.env.NODE_ENV === "development") {
          console.warn("No valid theme settings found in storage, returning default dark theme.");
        }
        return this.ensureCompleteThemeSettings(this.predefinedThemes.dark);
      }

      // Ensure the loaded settings have all necessary properties
      return this.ensureCompleteThemeSettings(parsedSettings);

    } catch (error) {
      console.error("Error getting theme settings:", error)
      // Fallback to default dark theme in case of any error
      return this.ensureCompleteThemeSettings(this.predefinedThemes.dark);
    }
  }

  // Helper function to ensure all theme properties exist, merging with default if necessary
  private ensureCompleteThemeSettings(settings: any): ThemeSettings {
    const defaultTheme = this.predefinedThemes.dark; // Use dark as the base default

    // Basic structure check
    if (!settings || typeof settings !== 'object') {
      return defaultTheme;
    }

    // Deep merge function (simple version)
    const mergeDeep = (target: any, source: any): any => {
      const output = { ...target };
      if (isObject(target) && isObject(source)) {
        Object.keys(source).forEach(key => {
          if (isObject(source[key])) {
            if (!(key in target)) {
              output[key] = source[key];
            } else {
              output[key] = mergeDeep(target[key], source[key]);
            }
          } else {
            output[key] = source[key];
          }
        });
      }
      return output;
    };

    const isObject = (item: any): boolean => {
      return (item && typeof item === 'object' && !Array.isArray(item));
    };

    // Merge the loaded settings onto the default theme structure
    // This ensures all keys from the default theme are present
    const completeSettings = mergeDeep(defaultTheme, settings);

    // Ensure the 'theme' property matches a known predefined theme or is 'custom'
    const knownThemes = Object.keys(this.predefinedThemes);
    if (!knownThemes.includes(completeSettings.theme) && completeSettings.theme !== 'custom') {
        // If the theme name is invalid, check if settings match a predefined one
        let matchedTheme = 'custom'; // Default to custom if no match
        for (const [themeName, predefinedSettings] of Object.entries(this.predefinedThemes)) {
            // Simple comparison (could be deeper if needed)
            if (JSON.stringify(completeSettings.colors) === JSON.stringify(predefinedSettings.colors) &&
                JSON.stringify(completeSettings.fontSize) === JSON.stringify(predefinedSettings.fontSize) &&
                JSON.stringify(completeSettings.spacing) === JSON.stringify(predefinedSettings.spacing) &&
                completeSettings.fontFamily === predefinedSettings.fontFamily) {
                matchedTheme = themeName;
                break;
            }
        }
         console.warn(`Loaded theme name '${settings.theme}' is invalid or unknown. Setting to '${matchedTheme}'.`);
        completeSettings.theme = matchedTheme;
    }


    return completeSettings as ThemeSettings;
  }


  async setThemeSettings(settings: ThemeSettings): Promise<void> {
    try {
      // Ensure settings are complete before saving
      const completeSettings = this.ensureCompleteThemeSettings(settings);
      await this.storage.set("themeSettings", JSON.stringify(completeSettings))
      // Apply the theme immediately after setting
      this.applyThemeToRoot(completeSettings)
    } catch (error) {
      console.error("Error setting theme settings:", error)
    }
  }

  watchTheme(callback: (settings: ThemeSettings) => void): void {
    this.storage.watch({
      themeSettings: (change) => {
        if (change.newValue) {
          try {
             let parsedSettings: any;
             if (typeof change.newValue === "string") {
               try {
                 parsedSettings = JSON.parse(change.newValue);
               } catch (e) {
                 console.error("Failed to parse watched theme settings from string:", e);
                 // Use default if parsing fails during watch
                 parsedSettings = this.predefinedThemes.dark;
               }
             } else {
               parsedSettings = change.newValue;
             }
             // Ensure completeness before calling callback
             const completeSettings = this.ensureCompleteThemeSettings(parsedSettings);
             callback(completeSettings)
             // Also apply the theme when it changes externally
             this.applyThemeToRoot(completeSettings)
          } catch (error) {
             console.error("Error processing watched theme settings:", error);
             // Fallback to applying default dark theme if processing fails
             const defaultSettings = this.ensureCompleteThemeSettings(this.predefinedThemes.dark);
             callback(defaultSettings);
             this.applyThemeToRoot(defaultSettings);
          }
        } else {
           // Handle case where settings might be removed or become invalid
           console.warn("Theme settings removed or became invalid in storage, applying default dark theme.");
           const defaultSettings = this.ensureCompleteThemeSettings(this.predefinedThemes.dark);
           callback(defaultSettings);
           this.applyThemeToRoot(defaultSettings);
        }
      }
    })
  }

  // Helper to inject Google Fonts link if needed
  private injectGoogleFont(font: string) {
    const localFonts = [
      "Arial",
      "Helvetica",
      "Verdana",
      "Tahoma",
      "Trebuchet MS",
      "Times New Roman",
      "Georgia",
      "Garamond",
      "Courier New",
      "Noto Sans",
      "Tagesschrift",
      "Underdog",
      "Space Grotesk",
      "Gidole",
      "M PLUS Code Latin"
    ];
    if (!font || localFonts.includes(font)) return;
    const fontParam = font.trim().replace(/ /g, "+");
    // Load a wider range of weights to support font-weight customization
    const href = `https://fonts.googleapis.com/css?family=${fontParam}:100,200,300,400,500,600,700,800,900&display=swap`;
    if (!document.querySelector(`link[data-google-font="${fontParam}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.setAttribute("data-google-font", fontParam);
      document.head.appendChild(link);
    }
  }

  applyThemeToRoot(settings: ThemeSettings): void {
    const root = document.documentElement
    if (!root || !settings) return

    // Inject Google Font if needed
    this.injectGoogleFont(settings.fontFamily);

    // Apply font settings
    root.style.setProperty("--font-family", settings.fontFamily)
    root.style.setProperty("--font-weight", settings.fontWeight.toString())
    root.style.setProperty("--font-size-body", settings.fontSize.body)
    root.style.setProperty("--font-size-h1", settings.fontSize.h1)
    root.style.setProperty("--font-size-h2", settings.fontSize.h2)
    root.style.setProperty("--font-size-h3", settings.fontSize.h3)

    // Apply color settings
    root.style.setProperty("--color-background", settings.colors.background)
    root.style.setProperty("--color-background2", settings.colors.background2)
    root.style.setProperty("--color-text", settings.colors.text)
    root.style.setProperty("--color-primary", settings.colors.primary)
    root.style.setProperty("--color-secondary", settings.colors.secondary)
    root.style.setProperty("--color-border", settings.colors.border)
    root.style.setProperty("--color-button-hover", settings.colors.buttonHover)
    root.style.setProperty("--color-button-primary", settings.colors.button.primary)
    root.style.setProperty("--color-button-secondary", settings.colors.button.secondary)
    root.style.setProperty("--color-button-text", settings.colors.button.text)
    root.style.setProperty("--color-heading-h1", settings.colors.headings.h1)
    root.style.setProperty("--color-heading-h2", settings.colors.headings.h2)
    root.style.setProperty("--color-heading-h3", settings.colors.headings.h3)
    root.style.setProperty("--color-emphasis", settings.colors.emphasis)
    root.style.setProperty("--color-emphasis-gradient-1", settings.colors.emphasisGradient.color1)
    root.style.setProperty("--color-emphasis-gradient-2", settings.colors.emphasisGradient.color2)
    root.style.setProperty("--color-emphasis-gradient-3", settings.colors.emphasisGradient.color3)
    // Construct and apply the actual gradient for <em> tags
    const gradientString = `linear-gradient(to right, ${settings.colors.emphasisGradient.color1}, ${settings.colors.emphasisGradient.color2}, ${settings.colors.emphasisGradient.color3})`;
    root.style.setProperty("--emphasis-gradient", gradientString);
    root.style.setProperty("--color-bold", settings.colors.bold)
    root.style.setProperty("--color-citation", settings.colors.citation) // Add citation color variable
    root.style.setProperty("--color-lite-humor", settings.colors.liteHumor) // Add lite humor color variable

    // Apply spacing settings
    root.style.setProperty("--spacing-line-height", settings.spacing.lineHeight)
    root.style.setProperty("--spacing-paragraph", settings.spacing.paragraphSpacing)
    root.style.setProperty("--spacing-list", settings.spacing.listSpacing)
    root.style.setProperty("--spacing-list-indent", settings.spacing.listIndent)
  }
}

export const themeStorage = new ThemeStorage()

</code>


<notes>Some files may have been skipped, to save tokens or because they didn't seem relevant. Ask about them if needed.</notes>


These code files are from a browser extension that displays markdown in very customized styles and themes with gradients, etc. Use this information to know what to do with markdown so you can display it in 'spicier' ways :)