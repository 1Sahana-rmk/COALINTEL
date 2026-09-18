'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DocumentTable } from '@/components/documents/DocumentTable';
import { UploadModal } from '@/components/documents/UploadModal';
import { documentApi } from '@/lib/api/documentApi';
import { useScope } from '@/context/ScopeContext';
import { Upload, FileText, Database, ShieldCheck } from 'lucide-react';

export default function DocumentsPage() {
  const { selectedSubsidiary, setSelectedSubsidiary } = useScope();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('ALL');

  // React Query data fetching for document repository list
  const {
    data: documentData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['documents', selectedStatus, selectedSubsidiary],
    queryFn: () =>
      documentApi.getDocuments({
        status_filter: selectedStatus,
        subsidiary_filter: selectedSubsidiary,
      }),
    staleTime: 30000,
  });

  const documents = documentData?.items || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Document Repository & Digitization Hub"
        description="Centralized geological reports, annual performance reviews, RTI disclosures, and production audit files for Coal India Limited and CMPDI."
        breadcrumbs={[{ label: 'Document Repository' }]}
        badge={<Badge variant="amber">V2 Intelligence Hub</Badge>}
        actions={
          <Button
            variant="primary"
            leftIcon={<Upload className="h-4 w-4" />}
            onClick={() => setIsUploadModalOpen(true)}
          >
            Ingest Document
          </Button>
        }
      />

      {/* Main Document Data Table */}
      <DocumentTable
        documents={documents}
        loading={isLoading}
        onRefresh={() => refetch()}
        selectedStatus={selectedStatus}
        onStatusChange={setSelectedStatus}
        selectedSubsidiary={selectedSubsidiary}
        onSubsidiaryChange={setSelectedSubsidiary}
      />

      {/* Ingest Document Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => refetch()}
      />
    </div>
  );
}
