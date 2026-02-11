import {defineArrayMember, defineField, defineType} from 'sanity'

export default defineType({
  name: 'tro_post',
  title: 'TRO Post',
  type: 'document',
  fields: [
    defineField({
      name: 'caseNumber',
      title: 'Case Number',
      type: 'string',
    }),
    defineField({
      name: 'title',
      title: 'Title',
      type: 'string',
    }),
    defineField({
      name: 'content',
      title: 'Content',
      type: 'text',
    }),
    defineField({
      name: 'brand',
      title: 'Brand',
      type: 'string',
    }),
    // 品牌信息
    defineField({
      name: 'brandInfo',
      title: 'Brand Info',
      type: 'text',
      description: 'JSON string of brand information',
    }),
    defineField({
      name: 'lawDate',
      title: 'Law Date',
      type: 'date',
    }),
    defineField({
      name: 'lawFrom',
      title: 'Law From',
      type: 'string',
    }),
    defineField({
      name: 'lawFirm',
      title: 'Law Firm',
      type: 'string',
    }),
    // 维权类型
    defineField({
      name: 'lawType',
      title: 'Law Type',
      type: 'string',
    }),
    defineField({
      name: 'courtInfo',
      title: '法院信息',
      type: 'string',
    }),
    defineField({
      name: 'relatedCases',
      title: '相关案件',
      type: 'array',
      of: [defineArrayMember({type: 'string'})],
    }),
    defineField({
      name: 'goodsCategories',
      title: 'Goods Categories',
      type: 'string',
    }),
    defineField({
      name: 'images',
      title: 'Images',
      type: 'text',
      description: 'JSON string of images data',
    }),
  ],

  preview: {
    select: {
      title: 'title',
      subtitle: 'caseNumber',
    },
    prepare(selection) {
      const {title, subtitle} = selection
      return {...selection, title: title || 'Untitled', subtitle: subtitle && `Case: ${subtitle}`}
    },
  },
})
