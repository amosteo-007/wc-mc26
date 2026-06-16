"use client";

interface RadioOption {
  value: string;
  label: string;
  description?: string;
}

interface RadioGroupProps {
  options: RadioOption[];
  value: string;
  onChange: (value: string) => void;
}

export function RadioGroup({ options, value, onChange }: RadioGroupProps) {
  return (
    <div className="space-y-2">
      {options.map((opt) => (
        <label
          key={opt.value}
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
            value === opt.value
              ? "border-blue-600 bg-blue-600/10"
              : "border-gray-800 bg-gray-800/50 hover:border-gray-700"
          }`}
        >
          <input
            type="radio"
            className="mt-0.5 accent-blue-600"
            checked={value === opt.value}
            onChange={() => onChange(opt.value)}
          />
          <div>
            <div className="text-sm font-medium">{opt.label}</div>
            {opt.description && (
              <div className="text-xs text-gray-500 mt-0.5">{opt.description}</div>
            )}
          </div>
        </label>
      ))}
    </div>
  );
}
