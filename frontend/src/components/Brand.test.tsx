import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { Brand } from './Brand'
import { APP_NAME } from '../config/brand'

describe('Brand', () => {
  it('links to the workspace home', () => {
    render(<MemoryRouter><Brand /></MemoryRouter>)
    expect(screen.getByRole('link', { name: `${APP_NAME} home` })).toHaveAttribute('href', '/')
  })
})
