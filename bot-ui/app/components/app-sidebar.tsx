import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import { PlusIcon } from "@/components/icons";
import { MessageSquareText, FileQuestion, Copy, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRef, useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { uploadBlog, uploadFile } from "@/api/file";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PATHS = [
  {
    title: "Chat",
    url: "/",
    icon: MessageSquareText,
  },
  {
    title: "Quiz",
    url: "/quiz",
    icon: FileQuestion,
  },
  {
    title: "Flashcard",
    url: "/flashcard",
    icon: FileQuestion,
  },
];

export function AppSidebar() {
  const { setOpenMobile } = useSidebar();
  const [open, setOpen] = useState(false);
  const [isUploading, setUploading] = useState(false);
  const [fileType, setFileType] = useState("notes");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const blogUrlRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    const file = fileInputRef.current?.files?.[0];
    const blogUrl = blogUrlRef.current?.value;

    if (!file && !blogUrl) {
      return;
    }

    setUploading(true);

    try {
      await Promise.allSettled([
        file && uploadFile(file, fileType),
        blogUrl && uploadBlog(blogUrl),
      ]);
      setOpen(false);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <Sidebar className="group-data-[side=left]:border-r-0">
        <SidebarHeader>
          <SidebarMenu>
            <div className="flex flex-row justify-between items-center">
              <a
                href="/"
                onClick={() => {
                  setOpenMobile(false);
                }}
                className="flex flex-row gap-3 items-center"
              >
                <span className="text-lg font-semibold px-2 hover:bg-muted rounded-md cursor-pointer">
                  Cognisense
                </span>
              </a>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    type="button"
                    className="p-2 h-fit"
                    onClick={() => {
                      setOpen(true);
                    }}
                  >
                    <PlusIcon />
                  </Button>
                </TooltipTrigger>
                <TooltipContent align="end">Add Document</TooltipContent>
              </Tooltip>
            </div>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <SidebarMenu>
            {PATHS.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild>
                  <a href={item.url}>
                    <item.icon />
                    <span>{item.title}</span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarContent>
        <SidebarFooter></SidebarFooter>
      </Sidebar>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload your document</DialogTitle>
          </DialogHeader>
          <div className="grid items-center gap-4">
            <div className="grid w-full max-w-sm items-center gap-2">
              <Label htmlFor="doc-file">File</Label>
              <Input id="doc-file" type="file" ref={fileInputRef} />
            </div>
            <div className="grid w-full max-w-sm items-center gap-2">
              <Label htmlFor="doc-type">Type</Label>
              <Select value={fileType} onValueChange={setFileType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select file type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="notes">
                    Notes: personal notes, chat discussion
                  </SelectItem>
                  <SelectItem value="documents">
                    Docs: any text files in 3 formats txt pdf docx
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Separator />
            <div className="grid w-full max-w-sm items-center gap-2">
              <Label htmlFor="blog-url">Blog Link</Label>
              <Input
                id="blog-url"
                type="text"
                placeholder="https://abc.com"
                ref={blogUrlRef}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" onClick={handleSubmit} disabled={isUploading}>
              {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isUploading ? "Uploading..." : "Upload"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
