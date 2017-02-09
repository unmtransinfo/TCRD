#!/usr/bin/perl -w

use strict;

$_ = <>;

my %gene_score = ();
my %gene_count = ();
my $count = 0;
my $prevpmid = 0;
while (<>) {
  s/\r?\n//;
  my ($pmid, $genes, undef) = split /\t/;
  if ($pmid != $prevpmid) {
    foreach my $gene (keys %gene_count) {
      $gene_score{$gene} = 0 unless exists $gene_score{$gene};
      $gene_score{$gene} += $gene_count{$gene}/$count;
    }
    %gene_count = ();
    $count = 0;
    $prevpmid = $pmid;
  }
  foreach my $gene (split /;/, $genes) {
    $gene_count{$gene} = 0 unless exists $gene_count{$gene};
    $gene_count{$gene}++;
    $count++;
  }
}

foreach my $gene (keys %gene_score) {
  printf "%s\t%f\n", $gene, $gene_score{$gene};
}
