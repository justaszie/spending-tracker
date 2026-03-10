import * as React from "react"
import { Check, ChevronsUpDown, Tag, Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Badge } from "@/components/ui/badge"

interface CategorySelectorProps {
  category: string | null,
  existing: string[],
  onSelect: (category: string) => void
}

export function CategorySelector({ category, existing, onSelect }: CategorySelectorProps) {
  const [open, setOpen] = React.useState(false)
  const [searchValue, setSearchValue] = React.useState("")

  // Combine predefined categories with current one if it's custom
  const [allCategories, setAllCategories] = React.useState<string[]>(existing)

  const handleSelect = (value: string) => {
    onSelect(value)
    setOpen(false)
    setSearchValue("")
  }

  const getBadgeColor = (cat: string) => {
    const colors = [
      "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-900",
      "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-900",
      "bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-900",
      "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-900",
      "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-900",
    ];
    let hash = 0;
    for (let i = 0; i < cat.length; i++) {
      hash = cat.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }

  const isNewCategory = searchValue.length > 0 && !allCategories.some(c => c.toLowerCase() === searchValue.toLowerCase())

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between h-auto py-1.5 px-2 min-h-[32px] text-left font-normal group hover:bg-muted/50 border border-transparent hover:border-border",
            !category && "text-muted-foreground border-dashed border-border"
          )}
        >
          {category ? (
            <Badge
              variant="outline"
              className={cn("font-medium border px-1.5 py-0.5 rounded-sm whitespace-nowrap", getBadgeColor(category))}
            >
              {category}
            </Badge>
          ) : (
            <span className="text-muted-foreground group-hover:text-foreground transition-colors">Select Category...</span>
          )}
          {!category && <Tag className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[280px] p-0 shadow-lg" align="start">
        <Command>
          <CommandInput
            placeholder="Search or type new category..."
            className="h-9"
            value={searchValue}
            onValueChange={setSearchValue}
          />
          <CommandList className="max-h-[300px]">
            {isNewCategory && (
              <CommandGroup heading="New Category">
                <CommandItem
                  value={searchValue}
                  onSelect={() => {
                    setAllCategories(prev => [...prev, searchValue])
                    handleSelect(searchValue)
                  }}
                  className="text-sm cursor-pointer py-2"
                >
                  <Plus className="mr-2 h-4 w-4 text-primary" />
                  <span>Create "{searchValue}"</span>
                </CommandItem>
              </CommandGroup>
            )}
            <CommandGroup heading="Categories">
              {allCategories
                .filter(c => c.toLowerCase().includes(searchValue.toLowerCase()))
                .map((cat) => (
                <CommandItem
                  key={cat}
                  value={cat}
                  onSelect={() => handleSelect(cat)}
                  className="text-sm cursor-pointer py-2"
                >
                  <div className="flex items-center w-full">
                    <div className={cn("w-2 h-2 rounded-full mr-2", getBadgeColor(cat).split(" ")[0].replace("text-", "bg-"))}></div>
                    <span>{cat}</span>
                    {category === cat && (
                      <Check className="ml-auto h-3 w-3 opacity-100 text-primary" />
                    )}
                  </div>
                </CommandItem>
              ))}
              {allCategories.filter(c => c.toLowerCase().includes(searchValue.toLowerCase())).length === 0 && !isNewCategory && (
                <div className="py-6 text-center text-sm text-muted-foreground">No categories found.</div>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
