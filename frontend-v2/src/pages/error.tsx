import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

interface ErrorPageProps {
  title?: string;
  message?: string;
}

export default function ErrorPage({
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again later.",
}: ErrorPageProps) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md mx-4">
        <CardContent className="pt-6">
          <div className="flex mb-4 gap-2">
            <AlertCircle className="h-8 w-8 text-red-500" />
            <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          </div>

          <p className="mt-4 text-sm text-gray-600">{message}</p>
        </CardContent>
      </Card>
    </div>
  );
}

