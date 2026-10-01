import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/manage'],
    },
    sitemap: 'https://fund-ui.vercel.app/sitemap.xml',
  };
}
