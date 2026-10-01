import { MetadataRoute } from 'next';
import { getFundIndex } from '@/lib/data';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://fund-ui.vercel.app';
  const index = await getFundIndex();

  const fundRoutes: MetadataRoute.Sitemap = (index?.funds || []).map((f) => ({
    url: `${baseUrl}/fund/${f.id}`,
    lastModified: new Date(),
    changeFrequency: 'monthly',
    priority: 0.8,
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1.0,
    },
    ...fundRoutes,
  ];
}
