import { Helmet } from "react-helmet-async";

interface MetaTagsProps {
  title: string;
  description?: string;
  image?: string;
}

export default function MetaTags({
  title,
  description = "SVASTRA+ Healthcare Authentication Platform",
  image = "/og-image.png",
}: MetaTagsProps) {
  return (
    <Helmet>
      <title>{title}</title>

      <meta name="description" content={description} />
      <meta name="theme-color" content="#0f766e" />

      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />
      <meta property="og:type" content="website" />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />
    </Helmet>
  );
}